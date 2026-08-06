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

SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_viii"
FIGURES_DIR = ROOT / "docs" / "figures"
TABLES_DIR = ROOT / "docs" / "tables"

SUMMARY_PATH = SUPPORT_DIR / "part_viii_risk_stress_summary.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = TABLES_DIR / "part_viii_risk_stress_results.md"

FIGURE_TAIL_RISK = FIGURES_DIR / "figure_8_1_tail_risk_comparison.png"
FIGURE_VAR_ES = FIGURES_DIR / "figure_8_2_var_es_canonical_backtesting.png"
FIGURE_DRAWDOWN = FIGURES_DIR / "figure_8_3_drawdown_depth_distribution.png"
FIGURE_MONTE_CARLO = FIGURES_DIR / "figure_8_4_monte_carlo_risk_probabilities.png"
FIGURE_HISTORICAL_REVERSE = FIGURES_DIR / "figure_8_5_historical_reverse_stress.png"
FIGURE_COUNTERFACTUAL = FIGURES_DIR / "figure_8_6_counterfactual_reverse_stress_scope.png"

FIGURE_PATHS = [
    FIGURE_TAIL_RISK,
    FIGURE_VAR_ES,
    FIGURE_DRAWDOWN,
    FIGURE_MONTE_CARLO,
    FIGURE_HISTORICAL_REVERSE,
    FIGURE_COUNTERFACTUAL,
]

SOURCE_FILES = {
    "tail_risk": "tail_risk.json",
    "var_es_backtesting": "var_es_backtesting.json",
    "drawdown_duration_recovery": "drawdown_duration_recovery.json",
    "historical_block_monte_carlo": ("historical_block_monte_carlo.json"),
    "historical_reverse_stress": ("historical_reverse_stress.json"),
    "counterfactual_reverse_stress": ("counterfactual_reverse_stress.json"),
}

SOURCE_SHA256 = {
    "tail_risk": ("29b9d94ec87da8249ae32086084bf1956f6f36bd39f0ff3db624216a67b68c56"),
    "var_es_backtesting": ("c1d74d449a23c1de99a5a701d97457e263f3957b796f2d1b30142a8b877fba8b"),
    "drawdown_duration_recovery": (
        "aac55eeef0278cbf70ee1f7816c1822d657bdc0c7b2013e65a3b6020cbd16a2d"
    ),
    "historical_block_monte_carlo": (
        "ddae15816201f3524eb9d8914838fda2b9cae051d7a6aecca37338afb1c9afb3"
    ),
    "historical_reverse_stress": (
        "679ef9da38ccaacab70b83594e460093d5c26fe975488d2a30403cae1ca5cbf5"
    ),
    "counterfactual_reverse_stress": (
        "8a5b35f8c9bd8da227802223c1018ac05a8e7b1ec5bd66a4e5a98b35d004aeb0"
    ),
}

EXPECTED_SECTIONS = {name: name for name in SOURCE_FILES}

MODEL = "Nostra AI V5.246"
SOURCE_RELEASE = "v0.3.0"
PERIOD_START = "2020-05-14"
PERIOD_END = "2026-06-02"
OBSERVATIONS = 2211
ANNUALIZATION = 365

NOSTRA_COLOR = "#1f77b4"
BTC_COLOR = "#8a8a8a"
CONDITIONAL_COLOR = "#ff7f0e"
LIGHT_NEUTRAL_COLOR = "#c7c7c7"
GRID_COLOR = "#d9d9d9"
AXIS_COLOR = "#777777"
TEXT_COLOR = "#222222"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValueError(message)


def close(
    observed: float,
    expected: float,
    tolerance: float = 1e-10,
) -> bool:
    return math.isclose(
        observed,
        expected,
        rel_tol=tolerance,
        abs_tol=tolerance,
    )


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
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def format_number(
    value: float,
    decimals: int = 2,
) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def format_percent(
    value: float,
    decimals: int = 2,
) -> str:
    return f"{value * 100:.{decimals}f} %".replace(".", ",")


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
            (f"Empreinte source non conforme pour {filename}: {observed_sha}"),
        )

        payload = json.loads(path.read_text(encoding="utf-8"))

        require(
            payload.get("schema_version") == 1,
            (f"Version de schéma non conforme pour {filename}."),
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


def records_by_key(
    records: list[dict[str, Any]],
    key: str,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}

    for record in records:
        value = str(record[key])

        require(
            value not in indexed,
            f"Doublon détecté pour {key}={value}.",
        )

        indexed[value] = record

    return indexed


def validate_tail_risk(
    data: dict[str, Any],
) -> None:
    require(
        data["method"] == "historical_var_and_expected_shortfall",
        "Méthode de risque de queue non conforme.",
    )

    records = data["records"]

    require(
        isinstance(records, list) and len(records) == 2,
        "Deux portefeuilles sont attendus.",
    )

    indexed = records_by_key(records, "portfolio")

    require(
        set(indexed) == {"nostra_ai", "bitcoin_benchmark"},
        "Portefeuilles de risque de queue non conformes.",
    )

    nostra = indexed["nostra_ai"]
    bitcoin = indexed["bitcoin_benchmark"]

    for record in records:
        require(
            int(record["observations"]) == OBSERVATIONS,
            "Nombre d'observations de queue non conforme.",
        )
        require(
            record["historical_es_95_daily"] >= record["historical_var_95_daily"],
            "ES 95 % inférieure à la VaR 95 %.",
        )
        require(
            record["historical_es_99_daily"] >= record["historical_var_99_daily"],
            "ES 99 % inférieure à la VaR 99 %.",
        )
        require(
            record["historical_var_99_daily"] >= record["historical_var_95_daily"],
            "VaR 99 % inférieure à la VaR 95 %.",
        )
        require(
            record["historical_es_99_daily"] >= record["historical_es_95_daily"],
            "ES 99 % inférieure à l'ES 95 %.",
        )

    require(
        close(
            float(nostra["historical_var_95_daily"]),
            0.02036101,
        ),
        "VaR 95 % Nostra non conforme.",
    )
    require(
        close(
            float(nostra["historical_es_95_daily"]),
            0.03207062,
        ),
        "ES 95 % Nostra non conforme.",
    )
    require(
        close(
            float(nostra["historical_var_99_daily"]),
            0.03876511,
        ),
        "VaR 99 % Nostra non conforme.",
    )
    require(
        close(
            float(nostra["historical_es_99_daily"]),
            0.05297551,
        ),
        "ES 99 % Nostra non conforme.",
    )

    for metric in (
        "historical_var_95_daily",
        "historical_es_95_daily",
        "historical_var_99_daily",
        "historical_es_99_daily",
    ):
        require(
            nostra[metric] < bitcoin[metric],
            (f"Le risque de queue Nostra doit être inférieur au bitcoin pour {metric}."),
        )


def validate_var_es(
    data: dict[str, Any],
) -> None:
    require(
        data["decision_status"] == "PASS_WITH_OBSERVATION",
        "Statut VaR/ES non conforme.",
    )
    require(
        data["methodological_status"] == "accepted_with_observations",
        "Statut méthodologique VaR/ES non conforme.",
    )
    require(
        data["canonical_calibration_window_days"] == 365,
        "Fenêtre canonique VaR/ES non conforme.",
    )
    require(
        data["observations"] == OBSERVATIONS,
        "Nombre d'observations VaR/ES non conforme.",
    )
    require(
        data["forecast_design"] == ("strictly trailing historical simulation without look-ahead"),
        "Conception causale VaR/ES non conforme.",
    )

    results = data["canonical_results"]

    require(
        isinstance(results, list) and len(results) == 4,
        "Quatre résultats canoniques VaR/ES attendus.",
    )
    require(
        data["canonical_traffic_light_counts"]
        == {
            "AMBER": 1,
            "GREEN": 3,
            "RED": 0,
        },
        "Feux canoniques VaR/ES non conformes.",
    )
    require(
        data["all_sensitivity_traffic_light_counts"]
        == {
            "AMBER": 4,
            "GREEN": 7,
            "RED": 1,
        },
        "Feux de sensibilité VaR/ES non conformes.",
    )

    pvalue_keys = (
        "kupiec_p_value",
        "exact_binomial_p_value",
        "christoffersen_independence_p_value",
        "christoffersen_conditional_coverage_p_value",
        "es_normalized_tail_loss_bootstrap_p_value",
    )

    for record in results:
        require(
            record["traffic_light"] in {"GREEN", "AMBER"},
            "Résultat canonique rouge inattendu.",
        )

        for key in pvalue_keys:
            require(
                float(record[key]) >= 0.05,
                (f"Réjection canonique inattendue pour {key}."),
            )

    amber = [record for record in results if record["traffic_light"] == "AMBER"]

    require(
        len(amber) == 1,
        "Un résultat canonique amber est attendu.",
    )
    require(
        amber[0]["risk_period_days"] == 10
        and close(
            float(amber[0]["confidence_level"]),
            0.99,
        ),
        "Le résultat amber doit être le 10 jours à 99 %.",
    )
    require(
        "LOW_EXPECTED_EXCEPTION_COUNT" in amber[0]["reason_codes"],
        "La faible puissance du test 10 jours à 99 % manque.",
    )

    governance = data["governance_decision"]

    require(
        governance["approved_specification"] == "365-day trailing historical simulation",
        "Spécification canonique approuvée non conforme.",
    )
    require(
        governance["non_approved_specification"]
        == ("250-day calibration for 99 percent tail-risk measures"),
        "Spécification non approuvée non conforme.",
    )


def validate_drawdowns(
    data: dict[str, Any],
) -> None:
    require(
        data["decision_status"] == "PASS_WITH_OBSERVATION",
        "Statut drawdown non conforme.",
    )
    require(
        data["observations"] == OBSERVATIONS,
        "Nombre d'observations drawdown non conforme.",
    )
    require(
        data["right_censoring_disclosed"] is True,
        "La censure à droite doit être déclarée.",
    )
    require(
        data["daily_paths_disclosed"] is False,
        "Les trajectoires quotidiennes ne doivent pas être publiées.",
    )
    require(
        set(data["strategies"]) == {"V5246", "BUY_AND_HOLD"},
        "Stratégies drawdown non conformes.",
    )

    nostra = data["strategies"]["V5246"]
    bitcoin = data["strategies"]["BUY_AND_HOLD"]

    require(
        nostra["episode_count"] == 104,
        "Nombre d'épisodes Nostra non conforme.",
    )
    require(
        bitcoin["episode_count"] == 50,
        "Nombre d'épisodes bitcoin non conforme.",
    )
    require(
        nostra["unrecovered_episode_count"] == 1,
        "Un épisode Nostra non récupéré est attendu.",
    )
    require(
        bitcoin["unrecovered_episode_count"] == 1,
        "Un épisode bitcoin non récupéré est attendu.",
    )
    require(
        close(
            float(nostra["maximum_drawdown"]),
            -0.21390503503731573,
        ),
        "Perte maximale Nostra non conforme.",
    )
    require(
        close(
            float(bitcoin["maximum_drawdown"]),
            -0.7662925431645915,
        ),
        "Perte maximale bitcoin non conforme.",
    )
    require(
        nostra["maximum_drawdown"] > bitcoin["maximum_drawdown"],
        "La perte maximale Nostra doit être moins profonde.",
    )
    require(
        (nostra["longest_observed_episode"]["observed_duration_observations"]) == 239,
        "Durée maximale Nostra non conforme.",
    )
    require(
        (bitcoin["longest_observed_episode"]["observed_duration_observations"]) == 847,
        "Durée maximale bitcoin non conforme.",
    )


def validate_monte_carlo(
    data: dict[str, Any],
) -> None:
    require(
        data["method"] == "joint_moving_block_historical_resampling",
        "Méthode Monte-Carlo non conforme.",
    )

    records = data["records"]

    require(
        isinstance(records, list) and len(records) == 8,
        "Huit résultats Monte-Carlo sont attendus.",
    )

    expected_blocks = {7.0, 21.0, 30.0, 60.0}

    for portfolio in (
        "nostra_ai",
        "bitcoin_benchmark",
    ):
        portfolio_records = [record for record in records if record["portfolio"] == portfolio]

        require(
            {float(record["block_size"]) for record in portfolio_records} == expected_blocks,
            (f"Tailles de blocs Monte-Carlo non conformes pour {portfolio}."),
        )

    for record in records:
        require(
            int(record["repetitions"]) == 10_000,
            "Nombre de trajectoires Monte-Carlo non conforme.",
        )
        require(
            int(record["simulation_length_days"]) == 365,
            "Horizon Monte-Carlo non conforme.",
        )
        require(
            (0.5482 <= record["probability_nostra_beats_btc_terminal"] <= 0.5807),
            "Probabilité terminale comparative non conforme.",
        )
        require(
            (record["probability_nostra_has_lower_drawdown"] >= 0.9999),
            "Probabilité de drawdown inférieur non conforme.",
        )

    for block_size in expected_blocks:
        nostra = next(
            record
            for record in records
            if record["portfolio"] == "nostra_ai" and float(record["block_size"]) == block_size
        )
        bitcoin = next(
            record
            for record in records
            if record["portfolio"] == "bitcoin_benchmark"
            and float(record["block_size"]) == block_size
        )

        require(
            nostra["probability_terminal_loss"] < bitcoin["probability_terminal_loss"],
            ("La probabilité de perte terminale Nostra doit être inférieure."),
        )
        require(
            (
                nostra["probability_drawdown_below_minus_30pct"]
                < bitcoin["probability_drawdown_below_minus_30pct"]
            ),
            ("La probabilité de drawdown inférieur à -30 % doit être plus faible pour Nostra."),
        )


def validate_historical_reverse_stress(
    data: dict[str, Any],
) -> None:
    require(
        data["decision_status"] == "PASS_WITH_OBSERVATION",
        "Statut reverse stress historique non conforme.",
    )
    require(
        data["observations"] == OBSERVATIONS,
        ("Nombre d'observations reverse stress historique non conforme."),
    )
    require(
        data["economic_reconciliation"]["status"] == "PASS",
        "Réconciliation économique reverse stress en échec.",
    )

    global_results = data["global_results"]

    require(
        global_results["drawdown_episode_count"] == 104,
        "Nombre d'épisodes réconciliés non conforme.",
    )
    require(
        global_results["loss_breach_record_count"] == 40,
        "Nombre de franchissements non conforme.",
    )

    results = data["loss_level_results"]

    require(
        isinstance(results, list) and len(results) == 6,
        "Six seuils de perte sont attendus.",
    )

    indexed = {float(record["target_nav_loss"]): record for record in results}

    require(
        set(indexed) == {0.05, 0.10, 0.15, 0.20, 0.25, 0.30},
        "Seuils de reverse stress non conformes.",
    )

    expected_counts = {
        0.05: 25,
        0.10: 10,
        0.15: 4,
        0.20: 1,
        0.25: 0,
        0.30: 0,
    }

    for level, expected_count in expected_counts.items():
        require(
            indexed[level]["breach_episode_count"] == expected_count,
            f"Nombre de franchissements non conforme à {level}.",
        )

    require(
        sum(expected_counts.values()) == 40,
        "Réconciliation du nombre de franchissements en échec.",
    )

    require(
        indexed[0.25]["historically_breached"] is False,
        "Le seuil de 25 % ne doit pas être franchi.",
    )
    require(
        indexed[0.30]["historically_breached"] is False,
        "Le seuil de 30 % ne doit pas être franchi.",
    )


def validate_counterfactual_reverse_stress(
    data: dict[str, Any],
) -> None:
    require(
        data["verification_level"] == "artifact-verified",
        "Niveau de vérification contrefactuel non conforme.",
    )
    require(
        data["observations"] == OBSERVATIONS,
        ("Nombre d'observations reverse stress contrefactuel non conforme."),
    )
    require(
        data["total_scenarios"] == 4908,
        "Nombre total de scénarios contrefactuels non conforme.",
    )
    require(
        (
            data["inference_stage_scenarios"]
            + data["retraining_and_core_scenarios"]
            + data["refinement_scenarios"]
        )
        == data["total_scenarios"],
        "Réconciliation des scénarios contrefactuels en échec.",
    )
    require(
        data["refined_failure_frontiers"] == 87,
        "Nombre de frontières raffinées non conforme.",
    )
    require(
        data["refined_failure_families"] == 8,
        "Nombre de familles de rupture non conforme.",
    )
    require(
        data["dominant_vulnerability_class"] == "directional_core_freshness_and_integrity",
        "Classe de vulnérabilité dominante non conforme.",
    )
    require(
        data["isolated_input_corruption_failure_found"] is False,
        ("Une rupture isolée de corruption d'entrée ne doit pas être déclarée."),
    )
    require(
        data["all_phase_offsets_tested"] is True,
        "Tous les offsets de phase doivent être testés.",
    )
    require(
        data["daily_paths_disclosed"] is False,
        "Les trajectoires quotidiennes ne doivent pas être publiées.",
    )
    require(
        data["internal_variables_disclosed"] is False,
        "Les variables internes ne doivent pas être publiées.",
    )
    require(
        data["exact_private_settings_disclosed"] is False,
        "Les réglages privés ne doivent pas être publiés.",
    )


def validate_sources(
    payloads: dict[str, dict[str, Any]],
) -> None:
    validate_tail_risk(payloads["tail_risk"]["data"])
    validate_var_es(payloads["var_es_backtesting"]["data"])
    validate_drawdowns(payloads["drawdown_duration_recovery"]["data"])
    validate_monte_carlo(payloads["historical_block_monte_carlo"]["data"])
    validate_historical_reverse_stress(payloads["historical_reverse_stress"]["data"])
    validate_counterfactual_reverse_stress(payloads["counterfactual_reverse_stress"]["data"])


def build_tail_summary(
    data: dict[str, Any],
) -> dict[str, Any]:
    indexed = records_by_key(
        data["records"],
        "portfolio",
    )

    nostra = indexed["nostra_ai"]
    bitcoin = indexed["bitcoin_benchmark"]

    return {
        "method": data["method"],
        "records": data["records"],
        "comparisons": {
            "var_95_reduction_ratio": (
                1 - nostra["historical_var_95_daily"] / bitcoin["historical_var_95_daily"]
            ),
            "es_95_reduction_ratio": (
                1 - nostra["historical_es_95_daily"] / bitcoin["historical_es_95_daily"]
            ),
            "var_99_reduction_ratio": (
                1 - nostra["historical_var_99_daily"] / bitcoin["historical_var_99_daily"]
            ),
            "es_99_reduction_ratio": (
                1 - nostra["historical_es_99_daily"] / bitcoin["historical_es_99_daily"]
            ),
            "worst_daily_loss_difference": (
                abs(bitcoin["minimum_daily_return"]) - abs(nostra["minimum_daily_return"])
            ),
        },
        "limitations": data["limitations"],
    }


def build_drawdown_summary(
    data: dict[str, Any],
) -> dict[str, Any]:
    strategies = data["strategies"]
    nostra = strategies["V5246"]
    bitcoin = strategies["BUY_AND_HOLD"]

    return {
        "analysis_type": data["analysis_type"],
        "decision_status": data["decision_status"],
        "right_censoring_disclosed": (data["right_censoring_disclosed"]),
        "strategies": {
            "nostra_ai": nostra,
            "bitcoin_benchmark": bitcoin,
        },
        "comparisons": {
            "maximum_drawdown_reduction_points": (
                abs(bitcoin["maximum_drawdown"]) - abs(nostra["maximum_drawdown"])
            ),
            "longest_episode_reduction_observations": (
                (bitcoin["longest_observed_episode"]["observed_duration_observations"])
                - (nostra["longest_observed_episode"]["observed_duration_observations"])
            ),
            "time_under_water_share_difference": (
                nostra["time_under_water_share"] - bitcoin["time_under_water_share"]
            ),
            "recovery_rate_difference": (nostra["recovery_rate"] - bitcoin["recovery_rate"]),
        },
        "limitations": data["limitations"],
    }


def build_monte_carlo_summary(
    data: dict[str, Any],
) -> dict[str, Any]:
    records = data["records"]

    comparative = [record for record in records if record["portfolio"] == "nostra_ai"]

    beats = [record["probability_nostra_beats_btc_terminal"] for record in comparative]
    lower_drawdown = [record["probability_nostra_has_lower_drawdown"] for record in comparative]

    return {
        "method": data["method"],
        "records": records,
        "scope": {
            "block_sizes": [7, 21, 30, 60],
            "simulation_length_days": 365,
            "repetitions_per_configuration": 10_000,
            "joint_resampling": True,
        },
        "comparative_ranges": {
            "probability_nostra_beats_btc_terminal": {
                "minimum": min(beats),
                "maximum": max(beats),
            },
            "probability_nostra_has_lower_drawdown": {
                "minimum": min(lower_drawdown),
                "maximum": max(lower_drawdown),
            },
        },
        "limitations": data["limitations"],
    }


def build_summary(
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_records = []

    for name, filename in SOURCE_FILES.items():
        path = SOURCE_DIR / filename

        source_records.append(
            {
                "name": name,
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": SOURCE_SHA256[name],
                "section": payloads[name]["section"],
                "schema_version": payloads[name]["schema_version"],
            }
        )

    return {
        "schema_version": 1,
        "section": "part_viii_risk_stress",
        "model": MODEL,
        "source_release": SOURCE_RELEASE,
        "period": {
            "start": PERIOD_START,
            "end": PERIOD_END,
            "observations": OBSERVATIONS,
            "annualization": ANNUALIZATION,
        },
        "sources": source_records,
        "tail_risk": build_tail_summary(payloads["tail_risk"]["data"]),
        "var_es_backtesting": (payloads["var_es_backtesting"]["data"]),
        "drawdown_duration_recovery": (
            build_drawdown_summary(payloads["drawdown_duration_recovery"]["data"])
        ),
        "historical_block_monte_carlo": (
            build_monte_carlo_summary(payloads["historical_block_monte_carlo"]["data"])
        ),
        "historical_reverse_stress": (payloads["historical_reverse_stress"]["data"]),
        "counterfactual_reverse_stress": (payloads["counterfactual_reverse_stress"]["data"]),
        "consolidated_assessment": {
            "status": "FAVORABLE_WITH_MATERIAL_OBSERVATIONS",
            "findings": [
                (
                    "Les mesures historiques de VaR, "
                    "d'Expected Shortfall et de perte quotidienne "
                    "sont inférieures à celles du bitcoin passif."
                ),
                (
                    "La spécification canonique de backtesting "
                    "VaR/ES à 365 jours ne présente aucune "
                    "réjection formelle au seuil de 5 %."
                ),
                ("Le test à dix jours au seuil de 99 % demeure de faible puissance."),
                (
                    "La fenêtre de calibration de 250 jours "
                    "n'est pas approuvée pour les mesures "
                    "de risque de queue à 99 %."
                ),
                (
                    "Les drawdowns de Nostra AI sont moins "
                    "profonds et leur épisode maximal observé "
                    "est plus court que pour le bitcoin passif."
                ),
                (
                    "Le dernier drawdown de Nostra AI est "
                    "non récupéré à la clôture et censuré à droite."
                ),
                (
                    "Dans les simulations historiques par blocs, "
                    "Nostra AI présente un drawdown inférieur au "
                    "bitcoin dans 99,99 % à 100 % des trajectoires."
                ),
                (
                    "Nostra AI termine devant le bitcoin dans "
                    "54,82 % à 58,07 % des trajectoires simulées."
                ),
                (
                    "La réduction d'allocation avant ou au "
                    "franchissement d'une perte n'est ni immédiate "
                    "ni universelle dans l'historique."
                ),
                (
                    "Le reverse stress contrefactuel couvre "
                    "4 908 scénarios, 87 frontières raffinées "
                    "et huit familles de rupture."
                ),
                (
                    "La vulnérabilité dominante concerne la "
                    "fraîcheur et l'intégrité du cœur directionnel."
                ),
            ],
            "limitations": [
                ("Toutes les analyses sont historiques, rétrospectives et non prédictives."),
                ("Les mesures de queue historiques ne constituent pas des bornes de perte."),
                ("Les trajectoires Monte-Carlo sont des recombinaisons de séquences historiques."),
                (
                    "Les durées de drawdown observées ne "
                    "constituent pas des prévisions de récupération."
                ),
                (
                    "Les non-franchissements historiques de 25 % "
                    "et 30 % ne démontrent pas que ces pertes "
                    "sont impossibles."
                ),
                (
                    "Les trajectoires quotidiennes, variables "
                    "internes, réglages exacts et frontières "
                    "privées ne sont pas publiés."
                ),
                ("Aucune validation externe indépendante n'est revendiquée."),
            ],
        },
    }


def write_markdown(
    summary: dict[str, Any],
) -> None:
    tail = summary["tail_risk"]
    var_es = summary["var_es_backtesting"]
    drawdowns = summary["drawdown_duration_recovery"]
    monte_carlo = summary["historical_block_monte_carlo"]
    historical = summary["historical_reverse_stress"]
    counterfactual = summary["counterfactual_reverse_stress"]

    tail_records = records_by_key(
        tail["records"],
        "portfolio",
    )

    nostra_tail = tail_records["nostra_ai"]
    btc_tail = tail_records["bitcoin_benchmark"]

    lines = [
        "# Partie VIII — Risque, drawdowns et stress",
        "",
        (
            "Paquet institutionnel construit à partir des six "
            "exports quantitatifs gelés de la release v0.3.0."
        ),
        "",
        "## Tableau 8.1 — Risque de queue historique quotidien",
        "",
        "| Indicateur | Nostra AI | Bitcoin passif |",
        "|---|---:|---:|",
        (
            "| VaR historique 95 % | "
            f"{format_percent(nostra_tail['historical_var_95_daily'])} | "
            f"{format_percent(btc_tail['historical_var_95_daily'])} |"
        ),
        (
            "| Expected Shortfall 95 % | "
            f"{format_percent(nostra_tail['historical_es_95_daily'])} | "
            f"{format_percent(btc_tail['historical_es_95_daily'])} |"
        ),
        (
            "| VaR historique 99 % | "
            f"{format_percent(nostra_tail['historical_var_99_daily'])} | "
            f"{format_percent(btc_tail['historical_var_99_daily'])} |"
        ),
        (
            "| Expected Shortfall 99 % | "
            f"{format_percent(nostra_tail['historical_es_99_daily'])} | "
            f"{format_percent(btc_tail['historical_es_99_daily'])} |"
        ),
        (
            "| Pire rendement quotidien | "
            f"{format_percent(nostra_tail['minimum_daily_return'])} | "
            f"{format_percent(btc_tail['minimum_daily_return'])} |"
        ),
        (
            "| Meilleur rendement quotidien | "
            f"{format_percent(nostra_tail['maximum_daily_return'])} | "
            f"{format_percent(btc_tail['maximum_daily_return'])} |"
        ),
        "",
        ("Les estimations sont historiques et ne constituent pas des bornes de perte futures."),
        "",
        "## Tableau 8.2 — Backtesting canonique de la VaR et de l'ES",
        "",
        (
            "| Horizon | Niveau | Observations | Exceptions | "
            "Taux observé | Taux attendu | Kupiec | Binomial exact | "
            "Indépendance | Couverture conditionnelle | ES bootstrap | Statut |"
        ),
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for record in var_es["canonical_results"]:
        lines.append(
            "| "
            f"{record['risk_period_days']} j | "
            f"{format_percent(record['confidence_level'], 0)} | "
            f"{record['observations']} | "
            f"{record['exception_count']} | "
            f"{format_percent(record['exception_rate'])} | "
            f"{format_number(record['expected_exception_count'], 2)} / "
            f"{record['observations']} | "
            f"{format_number(record['kupiec_p_value'], 4)} | "
            f"{format_number(record['exact_binomial_p_value'], 4)} | "
            f"{format_number(record['christoffersen_independence_p_value'], 4)} | "
            f"{format_number(record['christoffersen_conditional_coverage_p_value'], 4)} | "
            f"{format_number(record['es_normalized_tail_loss_bootstrap_p_value'], 4)} | "
            f"{record['traffic_light']} |"
        )

    nostra_dd = drawdowns["strategies"]["nostra_ai"]
    btc_dd = drawdowns["strategies"]["bitcoin_benchmark"]

    lines.extend(
        [
            "",
            (
                "La spécification canonique utilise une fenêtre "
                "glissante de 365 jours. Le test à dix jours et "
                "99 % est classé AMBER en raison du faible nombre "
                "attendu d'exceptions."
            ),
            "",
            "## Tableau 8.3 — Drawdowns, durées et récupération",
            "",
            "| Indicateur | Nostra AI | Bitcoin passif |",
            "|---|---:|---:|",
            (f"| Nombre d'épisodes | {nostra_dd['episode_count']} | {btc_dd['episode_count']} |"),
            (
                "| Perte maximale | "
                f"{format_percent(nostra_dd['maximum_drawdown'])} | "
                f"{format_percent(btc_dd['maximum_drawdown'])} |"
            ),
            (
                "| Profondeur médiane | "
                f"{format_percent(nostra_dd['drawdown_depth_distribution']['median'])} | "
                f"{format_percent(btc_dd['drawdown_depth_distribution']['median'])} |"
            ),
            (
                "| Profondeur au quantile 95 % | "
                f"{format_percent(nostra_dd['drawdown_depth_distribution']['q95'])} | "
                f"{format_percent(btc_dd['drawdown_depth_distribution']['q95'])} |"
            ),
            (
                "| Durée observée médiane | "
                f"{format_number(nostra_dd['observed_duration_distribution']['median'], 1)} | "
                f"{format_number(btc_dd['observed_duration_distribution']['median'], 1)} |"
            ),
            (
                "| Durée observée maximale | "
                f"{format_number(nostra_dd['observed_duration_distribution']['maximum'], 0)} | "
                f"{format_number(btc_dd['observed_duration_distribution']['maximum'], 0)} |"
            ),
            (
                "| Part du temps sous le précédent plus-haut | "
                f"{format_percent(nostra_dd['time_under_water_share'])} | "
                f"{format_percent(btc_dd['time_under_water_share'])} |"
            ),
            (
                "| Taux de récupération | "
                f"{format_percent(nostra_dd['recovery_rate'])} | "
                f"{format_percent(btc_dd['recovery_rate'])} |"
            ),
            (
                "| Épisodes non récupérés à la clôture | "
                f"{nostra_dd['unrecovered_episode_count']} | "
                f"{btc_dd['unrecovered_episode_count']} |"
            ),
            "",
            (
                "Les épisodes non récupérés sont censurés à droite. "
                "Les durées observées ne constituent pas des "
                "prévisions de récupération."
            ),
            "",
            "## Tableau 8.4 — Monte-Carlo historique par blocs",
            "",
            (
                "| Portefeuille | Bloc | Perte terminale | "
                "Drawdown < -20 % | Drawdown < -30 % | "
                "Sharpe positif | Rendement terminal médian | "
                "Drawdown médian |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    records = sorted(
        monte_carlo["records"],
        key=lambda record: (
            record["portfolio"],
            record["block_size"],
        ),
    )

    for record in records:
        label = "Nostra AI" if record["portfolio"] == "nostra_ai" else "Bitcoin passif"

        lines.append(
            "| "
            f"{label} | "
            f"{int(record['block_size'])} j | "
            f"{format_percent(record['probability_terminal_loss'])} | "
            f"{format_percent(record['probability_drawdown_below_minus_20pct'])} | "
            f"{format_percent(record['probability_drawdown_below_minus_30pct'])} | "
            f"{format_percent(record['probability_sharpe_positive'])} | "
            f"{format_percent(record['terminal_return_median'])} | "
            f"{format_percent(record['maximum_drawdown_median'])} |"
        )

    lines.extend(
        [
            "",
            (
                "Chaque configuration comprend 10 000 trajectoires "
                "de 365 jours. Les deux séries sont rééchantillonnées "
                "conjointement afin de préserver leur relation "
                "historique dans les blocs sélectionnés."
            ),
            "",
            (
                "Selon la taille de bloc, Nostra AI termine devant "
                "le bitcoin dans 54,82 % à 58,07 % des trajectoires "
                "et présente un drawdown inférieur dans 99,99 % "
                "à 100 % des trajectoires."
            ),
            "",
            "## Tableau 8.5 — Reverse stress historique",
            "",
            (
                "| Seuil de perte sur la NAV | Franchi historiquement | "
                "Épisodes | Observations médianes jusqu'au franchissement | "
                "Réduction à la date du franchissement | "
                "Réduction d'au moins 25 % avant franchissement |"
            ),
            "|---:|---|---:|---:|---:|---:|",
        ]
    )

    for record in historical["loss_level_results"]:
        if record["historically_breached"]:
            median_observations = format_number(
                record["observations_to_breach"]["median"],
                1,
            )
            reduced_at_breach = format_percent(
                record["allocation_reaction_shares"]["reduced_at_breach"]
            )
            reduced_before = format_percent(
                record["allocation_reaction_shares"]["reduced_by_at_least_25pct_before_breach"]
            )
        else:
            median_observations = "Non applicable"
            reduced_at_breach = "Non applicable"
            reduced_before = "Non applicable"

        lines.append(
            "| "
            f"{format_percent(record['target_nav_loss'], 0)} | "
            f"{'Oui' if record['historically_breached'] else 'Non'} | "
            f"{record['breach_episode_count']} | "
            f"{median_observations} | "
            f"{reduced_at_breach} | "
            f"{reduced_before} |"
        )

    lines.extend(
        [
            "",
            (
                "Les pertes de 25 % et 30 % n'ont pas été observées "
                "dans l'historique. Ce non-franchissement ne "
                "constitue pas une borne de perte."
            ),
            "",
            (
                "La réduction de l'allocation n'a été ni immédiate "
                "ni universelle avant les franchissements matériels."
            ),
            "",
            "## Tableau 8.6 — Reverse stress contrefactuel",
            "",
            "| Indicateur | Résultat |",
            "|---|---:|",
            (f"| Scénarios totaux | {counterfactual['total_scenarios']} |"),
            (
                "| Scénarios au stade de l'inférence | "
                f"{counterfactual['inference_stage_scenarios']} |"
            ),
            (
                "| Scénarios de réentraînement et du cœur directionnel | "
                f"{counterfactual['retraining_and_core_scenarios']} |"
            ),
            (f"| Scénarios de raffinement | {counterfactual['refinement_scenarios']} |"),
            (
                "| Frontières de rupture raffinées | "
                f"{counterfactual['refined_failure_frontiers']} |"
            ),
            (f"| Familles de rupture | {counterfactual['refined_failure_families']} |"),
            (
                "| Répétitions aléatoires de bruit | "
                f"{counterfactual['randomized_repetitions']['noise']} |"
            ),
            (
                "| Répétitions d'injection d'état défavorable | "
                f"{counterfactual['randomized_repetitions']['adverse_state_injection']} |"
            ),
            (
                "| Rupture isolée par corruption d'entrée identifiée | "
                f"{'Oui' if counterfactual['isolated_input_corruption_failure_found'] else 'Non'} |"
            ),
            "",
            (
                "La classe de vulnérabilité dominante est la "
                "fraîcheur et l'intégrité du cœur directionnel."
            ),
            "",
            (
                "Les réglages exacts, les variables internes, "
                "les trajectoires quotidiennes et les frontières "
                "numériques privées ne sont pas publiés."
            ),
            "",
            "## Lecture consolidée",
            "",
        ]
    )

    for finding in summary["consolidated_assessment"]["findings"]:
        lines.append(f"- {finding}")

    lines.extend(
        [
            "",
            "### Limites",
            "",
        ]
    )

    for limitation in summary["consolidated_assessment"]["limitations"]:
        lines.append(f"- {limitation}")

    MARKDOWN_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def configure_plotting() -> None:
    matplotlib.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": AXIS_COLOR,
            "axes.labelcolor": TEXT_COLOR,
            "axes.titlecolor": TEXT_COLOR,
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "xtick.color": TEXT_COLOR,
            "ytick.color": TEXT_COLOR,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "font.size": 12,
            "legend.fontsize": 11,
            "savefig.facecolor": "white",
            "savefig.dpi": 180,
        }
    )


def style_axis(
    axis: plt.Axes,
    *,
    x_grid: bool = False,
    y_grid: bool = True,
) -> None:
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)

    if y_grid:
        axis.grid(
            axis="y",
            color=GRID_COLOR,
            linewidth=0.8,
            alpha=0.8,
        )

    if x_grid:
        axis.grid(
            axis="x",
            color=GRID_COLOR,
            linewidth=0.8,
            alpha=0.8,
        )

    axis.set_axisbelow(True)


def save_figure(
    figure: plt.Figure,
    path: Path,
) -> None:
    figure.tight_layout()
    figure.savefig(
        path,
        bbox_inches="tight",
    )
    plt.close(figure)


def plot_tail_risk(
    tail: dict[str, Any],
) -> None:
    records = records_by_key(
        tail["records"],
        "portfolio",
    )

    nostra = records["nostra_ai"]
    bitcoin = records["bitcoin_benchmark"]

    labels = [
        "VaR 95 %",
        "ES 95 %",
        "VaR 99 %",
        "ES 99 %",
    ]
    keys = [
        "historical_var_95_daily",
        "historical_es_95_daily",
        "historical_var_99_daily",
        "historical_es_99_daily",
    ]

    nostra_values = [float(nostra[key]) for key in keys]
    bitcoin_values = [float(bitcoin[key]) for key in keys]

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
    bitcoin_bars = axis.bar(
        positions + width / 2,
        bitcoin_values,
        width,
        label="Bitcoin passif",
        color=BTC_COLOR,
    )

    axis.set_title(
        "Risque de queue historique quotidien",
        pad=20,
    )
    axis.set_ylabel("Perte historique")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))
    axis.set_ylim(
        0,
        max(bitcoin_values) * 1.18,
    )

    axis.bar_label(
        nostra_bars,
        labels=[format_percent(value, 2) for value in nostra_values],
        padding=5,
        fontsize=11,
    )
    axis.bar_label(
        bitcoin_bars,
        labels=[format_percent(value, 2) for value in bitcoin_values],
        padding=5,
        fontsize=11,
    )

    style_axis(axis)
    axis.legend(
        loc="upper left",
        frameon=False,
    )

    save_figure(
        figure,
        FIGURE_TAIL_RISK,
    )


def canonical_label(
    record: dict[str, Any],
) -> str:
    confidence = round(float(record["confidence_level"]) * 100)

    return f"{int(record['risk_period_days'])} j\n{confidence} %"


def plot_var_es(
    var_es: dict[str, Any],
) -> None:
    records = sorted(
        var_es["canonical_results"],
        key=lambda record: (
            record["risk_period_days"],
            record["confidence_level"],
        ),
    )

    labels = [canonical_label(record) for record in records]
    observed = [float(record["exception_rate"]) for record in records]
    expected = [1.0 - float(record["confidence_level"]) for record in records]

    positions = np.arange(len(labels))
    width = 0.36

    figure, axis = plt.subplots(figsize=(16, 9))

    observed_bars = axis.bar(
        positions - width / 2,
        observed,
        width,
        label="Taux observé",
        color=NOSTRA_COLOR,
    )
    expected_bars = axis.bar(
        positions + width / 2,
        expected,
        width,
        label="Taux attendu",
        color=LIGHT_NEUTRAL_COLOR,
    )

    axis.set_title(
        "Couverture canonique de la VaR",
        pad=20,
    )
    axis.set_ylabel("Taux d'exceptions")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))
    axis.set_ylim(
        0,
        max(observed + expected) * 1.30,
    )

    axis.bar_label(
        observed_bars,
        labels=[format_percent(value, 2) for value in observed],
        padding=5,
        fontsize=11,
    )
    axis.bar_label(
        expected_bars,
        labels=[format_percent(value, 2) for value in expected],
        padding=5,
        fontsize=11,
    )

    for position, record in zip(
        positions,
        records,
        strict=True,
    ):
        axis.annotate(
            record["traffic_light"],
            (
                position,
                max(
                    record["exception_rate"],
                    1.0 - record["confidence_level"],
                ),
            ),
            xytext=(0, 25),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            color=(CONDITIONAL_COLOR if record["traffic_light"] == "AMBER" else TEXT_COLOR),
        )

    style_axis(axis)
    axis.legend(
        loc="upper right",
        frameon=False,
    )

    save_figure(
        figure,
        FIGURE_VAR_ES,
    )


def plot_drawdowns(
    drawdowns: dict[str, Any],
) -> None:
    nostra = drawdowns["strategies"]["nostra_ai"]
    bitcoin = drawdowns["strategies"]["bitcoin_benchmark"]

    labels = [
        "Médiane",
        "Quantile 95 %",
        "Maximum",
    ]

    nostra_values = [
        float(nostra["drawdown_depth_distribution"]["median"]),
        float(nostra["drawdown_depth_distribution"]["q95"]),
        float(nostra["drawdown_depth_distribution"]["maximum"]),
    ]
    bitcoin_values = [
        float(bitcoin["drawdown_depth_distribution"]["median"]),
        float(bitcoin["drawdown_depth_distribution"]["q95"]),
        float(bitcoin["drawdown_depth_distribution"]["maximum"]),
    ]

    positions = np.arange(len(labels))
    width = 0.34

    figure, axis = plt.subplots(figsize=(16, 9))

    nostra_bars = axis.bar(
        positions - width / 2,
        nostra_values,
        width,
        label="Nostra AI",
        color=NOSTRA_COLOR,
        edgecolor="white",
        linewidth=1.2,
        zorder=3,
    )
    bitcoin_bars = axis.bar(
        positions + width / 2,
        bitcoin_values,
        width,
        label="Bitcoin passif",
        color=BTC_COLOR,
        edgecolor="white",
        linewidth=1.2,
        zorder=3,
    )

    axis.set_title(
        "Distribution historique de la profondeur des épisodes de repli",
        pad=24,
    )
    axis.set_ylabel("Profondeur de l'episode")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))
    axis.set_ylim(
        0,
        max(bitcoin_values) * 1.12,
    )

    axis.bar_label(
        nostra_bars,
        labels=[format_percent(value, 2) for value in nostra_values],
        padding=6,
        fontsize=11,
    )
    axis.bar_label(
        bitcoin_bars,
        labels=[format_percent(value, 2) for value in bitcoin_values],
        padding=6,
        fontsize=11,
    )

    style_axis(axis)

    axis.legend(
        loc="upper left",
        ncol=2,
        frameon=False,
    )

    save_figure(
        figure,
        FIGURE_DRAWDOWN,
    )


def monte_carlo_record(
    records: list[dict[str, Any]],
    portfolio: str,
    block_size: int,
) -> dict[str, Any]:
    return next(
        record
        for record in records
        if record["portfolio"] == portfolio and int(record["block_size"]) == block_size
    )


def plot_monte_carlo(
    monte_carlo: dict[str, Any],
) -> None:
    records = monte_carlo["records"]
    block_sizes = [7, 21, 30, 60]

    nostra_loss = [
        float(
            monte_carlo_record(
                records,
                "nostra_ai",
                block_size,
            )["probability_terminal_loss"]
        )
        for block_size in block_sizes
    ]
    bitcoin_loss = [
        float(
            monte_carlo_record(
                records,
                "bitcoin_benchmark",
                block_size,
            )["probability_terminal_loss"]
        )
        for block_size in block_sizes
    ]
    nostra_drawdown = [
        float(
            monte_carlo_record(
                records,
                "nostra_ai",
                block_size,
            )["probability_drawdown_below_minus_30pct"]
        )
        for block_size in block_sizes
    ]
    bitcoin_drawdown = [
        float(
            monte_carlo_record(
                records,
                "bitcoin_benchmark",
                block_size,
            )["probability_drawdown_below_minus_30pct"]
        )
        for block_size in block_sizes
    ]

    figure, axis = plt.subplots(figsize=(16, 9))

    nostra_loss_line = axis.plot(
        block_sizes,
        nostra_loss,
        marker="o",
        markersize=7,
        linewidth=2.6,
        label="Nostra AI — perte terminale",
        color=NOSTRA_COLOR,
        zorder=4,
    )[0]

    bitcoin_loss_line = axis.plot(
        block_sizes,
        bitcoin_loss,
        marker="o",
        markersize=7,
        linewidth=2.6,
        label="Bitcoin passif — perte terminale",
        color=BTC_COLOR,
        zorder=4,
    )[0]

    nostra_drawdown_line = axis.plot(
        block_sizes,
        nostra_drawdown,
        marker="s",
        markersize=7,
        linewidth=2.6,
        linestyle="--",
        label="Nostra AI — repli supérieur à 30 %",
        color=NOSTRA_COLOR,
        zorder=4,
    )[0]

    bitcoin_drawdown_line = axis.plot(
        block_sizes,
        bitcoin_drawdown,
        marker="s",
        markersize=7,
        linewidth=2.6,
        linestyle="--",
        label="Bitcoin passif — repli supérieur à 30 %",
        color=CONDITIONAL_COLOR,
        zorder=4,
    )[0]

    axis.set_title(
        "Probabilités de risque dans les simulations historiques par blocs",
        pad=24,
    )
    axis.set_xlabel("Longueur du bloc historique")
    axis.set_ylabel("Fréquence empirique")
    axis.set_xticks(block_sizes)
    axis.set_xlim(
        4,
        76,
    )
    axis.set_ylim(
        0,
        0.86,
    )
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))

    direct_labels = [
        (
            nostra_loss_line,
            nostra_loss[-1],
            "Nostra AI — perte terminale",
            8,
        ),
        (
            bitcoin_loss_line,
            bitcoin_loss[-1],
            "Bitcoin — perte terminale",
            8,
        ),
        (
            nostra_drawdown_line,
            nostra_drawdown[-1],
            "Nostra AI — repli > 30 %",
            -10,
        ),
        (
            bitcoin_drawdown_line,
            bitcoin_drawdown[-1],
            "Bitcoin — repli > 30 %",
            8,
        ),
    ]

    for line, value, label, vertical_offset in direct_labels:
        axis.annotate(
            (f"{label} : {format_percent(value, 1)}"),
            xy=(
                block_sizes[-1],
                value,
            ),
            xytext=(
                12,
                vertical_offset,
            ),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=10,
            color=line.get_color(),
        )

    style_axis(axis)

    save_figure(
        figure,
        FIGURE_MONTE_CARLO,
    )


def plot_historical_reverse_stress(
    historical: dict[str, Any],
) -> None:
    breached = [
        record for record in historical["loss_level_results"] if record["historically_breached"]
    ]

    labels = [
        format_percent(
            float(record["target_nav_loss"]),
            0,
        )
        for record in breached
    ]
    counts = [int(record["breach_episode_count"]) for record in breached]
    medians = [float(record["observations_to_breach"]["median"]) for record in breached]

    positions = np.arange(len(labels))

    bubble_sizes = [320 + count * 38 for count in counts]

    figure, axis = plt.subplots(figsize=(16, 9))

    axis.plot(
        positions,
        medians,
        linewidth=2.4,
        color=CONDITIONAL_COLOR,
        alpha=0.82,
        zorder=2,
    )

    axis.scatter(
        positions,
        medians,
        s=bubble_sizes,
        color=NOSTRA_COLOR,
        edgecolors="white",
        linewidths=1.8,
        alpha=0.94,
        zorder=3,
    )

    axis.set_title(
        (
            "Franchissements historiques des seuils de perte\n"
            "La taille des bulles represente le nombre d'episodes"
        ),
        pad=24,
    )
    axis.set_xlabel("Seuil de perte depuis le précédent sommet")
    axis.set_ylabel("Observations medianes jusqu'au franchissement")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)

    axis.set_yscale("log")
    axis.set_ylim(
        4,
        240,
    )
    axis.set_yticks(
        [
            5,
            10,
            20,
            50,
            100,
            200,
        ]
    )
    axis.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())

    for position, count, median in zip(
        positions,
        counts,
        medians,
        strict=True,
    ):
        axis.text(
            position,
            median,
            str(count),
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="white",
            zorder=4,
        )

        axis.annotate(
            f"{format_number(median, 1)} observations",
            xy=(
                position,
                median,
            ),
            xytext=(
                0,
                -34,
            ),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=10,
            color=TEXT_COLOR,
        )

    style_axis(axis)

    save_figure(
        figure,
        FIGURE_HISTORICAL_REVERSE,
    )


def plot_counterfactual(
    counterfactual: dict[str, Any],
) -> None:
    labels = [
        "Inférence",
        "Réentraînement et cœur",
        "Raffinement",
    ]
    values = [
        counterfactual["inference_stage_scenarios"],
        counterfactual["retraining_and_core_scenarios"],
        counterfactual["refinement_scenarios"],
    ]

    positions = np.arange(len(labels))

    figure, axis = plt.subplots(figsize=(16, 9))

    bars = axis.barh(
        positions,
        values,
        color=[
            NOSTRA_COLOR,
            CONDITIONAL_COLOR,
            BTC_COLOR,
        ],
        height=0.58,
    )

    axis.set_title(
        "Périmètre du reverse stress contrefactuel",
        pad=20,
    )
    axis.set_xlabel("Nombre de scénarios, échelle logarithmique")
    axis.set_yticks(positions)
    axis.set_yticklabels(labels)
    axis.set_xscale("log")
    axis.invert_yaxis()

    axis.bar_label(
        bars,
        labels=[f"{value:,}".replace(",", " ") for value in values],
        padding=6,
        fontsize=12,
    )

    axis.text(
        0.99,
        0.05,
        (
            f"Total : {counterfactual['total_scenarios']:,} scénarios\n"
            f"Frontières raffinées : "
            f"{counterfactual['refined_failure_frontiers']}\n"
            f"Familles de rupture : "
            f"{counterfactual['refined_failure_families']}"
        ).replace(",", " "),
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=11,
        color=TEXT_COLOR,
    )

    style_axis(
        axis,
        x_grid=True,
        y_grid=False,
    )

    save_figure(
        figure,
        FIGURE_COUNTERFACTUAL,
    )


def generate_figures(
    summary: dict[str, Any],
) -> None:
    configure_plotting()

    plot_tail_risk(summary["tail_risk"])
    plot_var_es(summary["var_es_backtesting"])
    plot_drawdowns(summary["drawdown_duration_recovery"])
    plot_monte_carlo(summary["historical_block_monte_carlo"])
    plot_historical_reverse_stress(summary["historical_reverse_stress"])
    plot_counterfactual(summary["counterfactual_reverse_stress"])


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
        "package": "part_viii_risk_stress_report_support",
        "model": MODEL,
        "source_release": SOURCE_RELEASE,
        "period": {
            "start": PERIOD_START,
            "end": PERIOD_END,
            "observations": OBSERVATIONS,
            "annualization": ANNUALIZATION,
        },
        "status": (
            "Paquet institutionnel de support de la "
            "Partie VIII consacré au risque de queue, "
            "aux drawdowns, à la VaR/ES, au Monte-Carlo "
            "historique et aux reverse stress tests."
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
    SUPPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    TABLES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    print("PASS_PART_VIII_RISK_STRESS_SUPPORT_READY")
    print(f"Résumé : {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Tableaux : {MARKDOWN_PATH.relative_to(ROOT)}")
    print(f"Figures : {len(FIGURE_PATHS)}")
    print(f"Sources gelées réconciliées : {len(SOURCE_FILES)}")


if __name__ == "__main__":
    main()
