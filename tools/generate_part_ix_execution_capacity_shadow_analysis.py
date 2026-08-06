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
from matplotlib.ticker import PercentFormatter

from hilmarbench.execution import (
    ExecutionCostAssumptions,
    build_execution_scenario_surface,
    estimate_capacity_from_edge,
)

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"
SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_ix"
FIGURES_DIR = ROOT / "docs" / "figures"
TABLES_DIR = ROOT / "docs" / "tables"

SUMMARY_PATH = SUPPORT_DIR / "part_ix_execution_capacity_shadow_summary.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = TABLES_DIR / "part_ix_execution_capacity_shadow_results.md"

GENERATOR_PATH = ROOT / "tools" / "generate_part_ix_execution_capacity_shadow_analysis.py"

FIGURE_COST_CAGR = FIGURES_DIR / "figure_9_1_cost_delay_cagr.png"
FIGURE_COST_SHARPE = FIGURES_DIR / "figure_9_2_cost_delay_risk_adjusted_performance.png"
FIGURE_EXECUTION_SURFACE = FIGURES_DIR / "figure_9_3_synthetic_execution_cost_surface.png"
FIGURE_CAPACITY = FIGURES_DIR / "figure_9_4_synthetic_capacity_constraints.png"

FIGURE_PATHS = [
    FIGURE_COST_CAGR,
    FIGURE_COST_SHARPE,
    FIGURE_EXECUTION_SURFACE,
    FIGURE_CAPACITY,
]

SOURCE_FILES = {
    "execution_cost_delay": "execution_cost_delay.json",
    "shadow_monitoring": "shadow_monitoring.json",
}

SOURCE_SHA256 = {
    "execution_cost_delay": ("ae0485d907b9c3cb01fb26dbe05f95bbdc127491b31a458bfdb051fbc04ae38c"),
    "shadow_monitoring": ("6f7199b73f3423ab1eeb4c4cf7572939ddd0cb7f86b81fa3e5e2adb042e02d7d"),
}

MODEL = "Nostra AI V5.246"
SOURCE_RELEASE = "v0.3.0"
HISTORICAL_START = "2020-05-14"
HISTORICAL_END = "2026-06-02"
OBSERVATIONS = 2211
ANNUALIZATION = 365

REFERENCE_CANDIDATE = "artifact_verified_reference"
COMPARISON_CANDIDATE = "comparison_candidate_01"

COST_LEVELS = [0.0, 10.0, 25.0, 50.0, 75.0, 100.0]
DELAY_LEVELS = [0, 1, 2]

SYNTHETIC_ORDER_NOTIONALS = [
    250_000.0,
    1_000_000.0,
    4_000_000.0,
    10_000_000.0,
]
SYNTHETIC_DAILY_VOLUME = 100_000_000.0
SYNTHETIC_VOLATILITIES = [0.02, 0.04, 0.08]
SYNTHETIC_SLIPPAGE_LEVELS = [0.0, 5.0, 10.0, 25.0]
SYNTHETIC_EDGE_LEVELS = [8.0, 10.0, 12.0, 18.0, 25.0, 50.0, 100.0]

NOSTRA_COLOR = "#1f77b4"
SECONDARY_COLOR = "#ff7f0e"
TERTIARY_COLOR = "#6f6f6f"
LIGHT_COLOR = "#c9c9c9"
GRID_COLOR = "#dddddd"
TEXT_COLOR = "#222222"

SYNTHETIC_ASSUMPTIONS = ExecutionCostAssumptions(
    fee_bps=2.0,
    half_spread_bps=3.0,
    slippage_bps=5.0,
    impact_coefficient_bps=8.0,
    impact_exponent=0.5,
    reference_participation_rate=0.01,
    reference_volatility=0.04,
    maximum_participation_rate=0.10,
)


def require(condition: bool, message: str) -> None:
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


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
            f"Empreinte non conforme pour {filename}: {observed_sha}",
        )

        payload = json.loads(path.read_text(encoding="utf-8"))

        require(
            payload.get("schema_version") == 1,
            f"Schéma non conforme pour {filename}.",
        )
        require(
            payload.get("section") == name,
            f"Section non conforme pour {filename}.",
        )
        require(
            isinstance(payload.get("data"), dict),
            f"Bloc data absent pour {filename}.",
        )

        payloads[name] = payload

    return payloads


def validate_execution_source(data: dict[str, Any]) -> None:
    require(
        data.get("candidate_count") == 2,
        "Deux candidats d'exécution sont attendus.",
    )
    require(
        data.get("cost_levels_bps") == COST_LEVELS,
        "La grille de coûts n'est pas conforme.",
    )
    require(
        data.get("delay_levels_days") == DELAY_LEVELS,
        "La grille de délais n'est pas conforme.",
    )
    require(
        data.get("reference_selection")
        == "unique_complete_grid_reconciled_to_public_artifact_verified_aggregate",
        "La règle de sélection de la référence n'est pas conforme.",
    )

    reconciliation = float(data.get("reference_maximum_absolute_difference"))

    require(
        0.0 <= reconciliation <= 1e-12,
        "La réconciliation de la référence dépasse la tolérance.",
    )

    records = data.get("records")

    require(
        isinstance(records, list) and len(records) == 36,
        "La grille publique doit contenir exactement 36 enregistrements.",
    )

    expected_keys = {
        (candidate, cost, delay)
        for candidate in (REFERENCE_CANDIDATE, COMPARISON_CANDIDATE)
        for delay in DELAY_LEVELS
        for cost in COST_LEVELS
    }

    observed_keys: set[tuple[str, float, int]] = set()

    numeric_fields = (
        "annualized_volatility",
        "cagr",
        "calmar",
        "cost_bps",
        "final_equity",
        "maximum_drawdown",
        "sharpe",
        "sortino",
        "turnover_total",
    )

    for record in records:
        require(
            isinstance(record, dict),
            "Un enregistrement coûts-délais n'est pas un objet.",
        )

        candidate = str(record.get("candidate"))
        cost = float(record.get("cost_bps"))
        delay = int(record.get("delay_days"))

        key = (
            candidate,
            cost,
            delay,
        )

        require(
            key not in observed_keys,
            f"Doublon dans la grille coûts-délais : {key}",
        )

        observed_keys.add(key)

        for field in numeric_fields:
            value = float(record[field])

            require(
                math.isfinite(value),
                f"Valeur non finie pour {field}.",
            )

        require(
            float(record["final_equity"]) > 0.0,
            "Une equity finale doit être strictement positive.",
        )
        require(
            float(record["annualized_volatility"]) >= 0.0,
            "La volatilité ne peut pas être négative.",
        )
        require(
            float(record["maximum_drawdown"]) <= 0.0,
            "Le drawdown maximal doit être nul ou négatif.",
        )

    require(
        observed_keys == expected_keys,
        "La couverture de la grille coûts-délais est incomplète.",
    )


def validate_shadow_source(data: dict[str, Any]) -> None:
    expected = {
        "calendar_days": 25,
        "complete_month_claim": False,
        "coverage_ratio": 0.92,
        "first_observed_day": "2026-06-26",
        "human_approval_required": True,
        "last_observed_day": "2026-07-20",
        "missing_day_count": 2,
        "observed_days": 23,
        "pilot_or_limited_production_approval": False,
        "production_readiness_decision": "not_made",
        "technical_collection_complete": True,
    }

    require(
        data == expected,
        "Le snapshot shadow ne correspond pas à l'export public gelé.",
    )


def normalized_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "annualized_volatility": float(record["annualized_volatility"]),
                "cagr": float(record["cagr"]),
                "calmar": float(record["calmar"]),
                "candidate": str(record["candidate"]),
                "cost_bps": float(record["cost_bps"]),
                "delay_days": int(record["delay_days"]),
                "final_equity": float(record["final_equity"]),
                "maximum_drawdown": float(record["maximum_drawdown"]),
                "sharpe": float(record["sharpe"]),
                "sortino": float(record["sortino"]),
                "turnover_total": float(record["turnover_total"]),
            }
            for record in records
        ],
        key=lambda record: (
            str(record["candidate"]),
            int(record["delay_days"]),
            float(record["cost_bps"]),
        ),
    )


def find_record(
    records: list[dict[str, Any]],
    *,
    candidate: str,
    cost_bps: float,
    delay_days: int,
) -> dict[str, Any]:
    matches = [
        record
        for record in records
        if (
            record["candidate"] == candidate
            and close(float(record["cost_bps"]), cost_bps)
            and int(record["delay_days"]) == delay_days
        )
    ]

    require(
        len(matches) == 1,
        (
            "Scénario introuvable ou non unique : "
            f"{candidate}, {cost_bps} bps, {delay_days} jour(s)."
        ),
    )

    return matches[0]


def build_synthetic_execution_surface() -> list[dict[str, Any]]:
    frame = build_execution_scenario_surface(
        order_notionals=SYNTHETIC_ORDER_NOTIONALS,
        daily_volume_notionals=[SYNTHETIC_DAILY_VOLUME],
        daily_volatilities=SYNTHETIC_VOLATILITIES,
        slippage_bps_values=SYNTHETIC_SLIPPAGE_LEVELS,
        assumptions=SYNTHETIC_ASSUMPTIONS,
    )

    records: list[dict[str, Any]] = []

    for raw in frame.to_dict(orient="records"):
        records.append(
            {
                "order_notional": float(raw["order_notional"]),
                "daily_volume_notional": float(raw["daily_volume_notional"]),
                "daily_volatility": float(raw["daily_volatility"]),
                "participation_rate": float(raw["participation_rate"]),
                "fee_bps": float(raw["fee_bps"]),
                "spread_bps": float(raw["spread_bps"]),
                "slippage_bps": float(raw["slippage_bps"]),
                "market_impact_bps": float(raw["market_impact_bps"]),
                "total_cost_bps": float(raw["total_cost_bps"]),
                "total_cost_notional": float(raw["total_cost_notional"]),
                "within_participation_limit": bool(raw["within_participation_limit"]),
            }
        )

    require(
        len(records) == 48,
        "La surface synthétique doit contenir 48 scénarios.",
    )

    return records


def build_synthetic_capacity_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for daily_volatility in SYNTHETIC_VOLATILITIES:
        for expected_edge in SYNTHETIC_EDGE_LEVELS:
            capacity = estimate_capacity_from_edge(
                expected_gross_edge_bps=expected_edge,
                daily_volume_notional=SYNTHETIC_DAILY_VOLUME,
                daily_volatility=daily_volatility,
                assumptions=SYNTHETIC_ASSUMPTIONS,
            )

            records.append(
                {
                    "expected_gross_edge_bps": float(capacity.expected_gross_edge_bps),
                    "daily_volume_notional": SYNTHETIC_DAILY_VOLUME,
                    "daily_volatility": daily_volatility,
                    "maximum_notional": float(capacity.maximum_notional),
                    "participation_rate": float(capacity.participation_rate),
                    "estimated_cost_bps": float(capacity.estimated_cost_bps),
                    "residual_edge_bps": float(capacity.residual_edge_bps),
                    "binding_constraint": capacity.binding_constraint,
                }
            )

    require(
        len(records) == 21,
        "La grille synthétique de capacité doit contenir 21 scénarios.",
    )

    return records


def build_summary(
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    execution_data = sources["execution_cost_delay"]["data"]
    shadow_data = sources["shadow_monitoring"]["data"]

    validate_execution_source(execution_data)
    validate_shadow_source(shadow_data)

    all_records = normalized_records(execution_data["records"])

    reference_records = [
        record for record in all_records if record["candidate"] == REFERENCE_CANDIDATE
    ]
    comparison_records = [
        record for record in all_records if record["candidate"] == COMPARISON_CANDIDATE
    ]

    baseline = find_record(
        reference_records,
        candidate=REFERENCE_CANDIDATE,
        cost_bps=25.0,
        delay_days=0,
    )
    high_cost = find_record(
        reference_records,
        candidate=REFERENCE_CANDIDATE,
        cost_bps=100.0,
        delay_days=0,
    )
    delayed = find_record(
        reference_records,
        candidate=REFERENCE_CANDIDATE,
        cost_bps=25.0,
        delay_days=2,
    )
    combined_stress = find_record(
        reference_records,
        candidate=REFERENCE_CANDIDATE,
        cost_bps=100.0,
        delay_days=2,
    )

    synthetic_surface = build_synthetic_execution_surface()
    synthetic_capacity = build_synthetic_capacity_records()

    source_records = []

    for name, filename in SOURCE_FILES.items():
        path = SOURCE_DIR / filename

        source_records.append(
            {
                "name": name,
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": SOURCE_SHA256[name],
                "schema_version": 1,
                "section": name,
            }
        )

    return {
        "schema_version": 1,
        "section": "part_ix_execution_capacity_shadow",
        "model": MODEL,
        "source_release": SOURCE_RELEASE,
        "historical_evaluation": {
            "start": HISTORICAL_START,
            "end": HISTORICAL_END,
            "observations": OBSERVATIONS,
            "annualization": ANNUALIZATION,
        },
        "sources": source_records,
        "historical_cost_delay": {
            "verification_level": "artifact-verified",
            "candidate_count": 2,
            "record_count": 36,
            "reference_record_count": len(reference_records),
            "comparison_record_count": len(comparison_records),
            "cost_levels_bps": COST_LEVELS,
            "delay_levels_days": DELAY_LEVELS,
            "reference_reconciliation_max_abs_delta": float(
                execution_data["reference_maximum_absolute_difference"]
            ),
            "reference_records": reference_records,
            "comparison_records": comparison_records,
            "selected_reference_scenarios": {
                "baseline_25bps_0day": baseline,
                "high_cost_100bps_0day": high_cost,
                "delay_25bps_2days": delayed,
                "combined_100bps_2days": combined_stress,
            },
            "sensitivity_deltas": {
                "high_cost_vs_baseline": {
                    "cagr_change": (float(high_cost["cagr"]) - float(baseline["cagr"])),
                    "sharpe_change": (float(high_cost["sharpe"]) - float(baseline["sharpe"])),
                    "maximum_drawdown_change": (
                        float(high_cost["maximum_drawdown"]) - float(baseline["maximum_drawdown"])
                    ),
                    "final_equity_change": (
                        float(high_cost["final_equity"]) - float(baseline["final_equity"])
                    ),
                },
                "two_day_delay_vs_baseline": {
                    "cagr_change": (float(delayed["cagr"]) - float(baseline["cagr"])),
                    "sharpe_change": (float(delayed["sharpe"]) - float(baseline["sharpe"])),
                    "maximum_drawdown_change": (
                        float(delayed["maximum_drawdown"]) - float(baseline["maximum_drawdown"])
                    ),
                    "final_equity_change": (
                        float(delayed["final_equity"]) - float(baseline["final_equity"])
                    ),
                },
                "combined_stress_vs_baseline": {
                    "cagr_change": (float(combined_stress["cagr"]) - float(baseline["cagr"])),
                    "sharpe_change": (float(combined_stress["sharpe"]) - float(baseline["sharpe"])),
                    "maximum_drawdown_change": (
                        float(combined_stress["maximum_drawdown"])
                        - float(baseline["maximum_drawdown"])
                    ),
                    "final_equity_change": (
                        float(combined_stress["final_equity"]) - float(baseline["final_equity"])
                    ),
                },
            },
        },
        "generic_execution_framework": {
            "status": "methodologically_available_not_real_world_calibrated",
            "cost_decomposition": [
                "fee",
                "half_spread",
                "slippage",
                "market_impact",
            ],
            "impact_model": ("power_law_participation_scaled_by_daily_volatility"),
            "default_impact_exponent": 0.5,
            "capacity_constraints": [
                "fixed_cost",
                "expected_edge",
                "participation_limit",
            ],
            "synthetic_assumptions": {
                "fee_bps": SYNTHETIC_ASSUMPTIONS.fee_bps,
                "half_spread_bps": SYNTHETIC_ASSUMPTIONS.half_spread_bps,
                "slippage_bps": SYNTHETIC_ASSUMPTIONS.slippage_bps,
                "impact_coefficient_bps": (SYNTHETIC_ASSUMPTIONS.impact_coefficient_bps),
                "impact_exponent": SYNTHETIC_ASSUMPTIONS.impact_exponent,
                "reference_participation_rate": (
                    SYNTHETIC_ASSUMPTIONS.reference_participation_rate
                ),
                "reference_volatility": (SYNTHETIC_ASSUMPTIONS.reference_volatility),
                "maximum_participation_rate": (SYNTHETIC_ASSUMPTIONS.maximum_participation_rate),
                "daily_volume_notional": SYNTHETIC_DAILY_VOLUME,
            },
            "synthetic_execution_surface": synthetic_surface,
            "synthetic_capacity_records": synthetic_capacity,
            "real_capacity_estimate_available": False,
            "real_calibration_inputs_available": {
                "client_order_data": False,
                "broker_execution_data": False,
                "venue_level_data": False,
                "observed_slippage_distribution": False,
                "calibrated_market_impact_parameters": False,
                "client_specific_participation_policy": False,
            },
        },
        "shadow_monitoring": {
            **shadow_data,
            "evidence_class": "internal_shadow_operational_evidence",
            "performance_outcome_metrics_disclosed": False,
            "client_orders_executed": False,
            "client_production_use": False,
            "external_independent_validation": False,
        },
        "outcome_analysis": {
            "status": "LIMITED_OBSERVATION_WINDOW",
            "historical_to_shadow_performance_comparison_available": False,
            "reason": (
                "The frozen public shadow export contains operational coverage "
                "information but no controlled performance outcome series."
            ),
            "authorized_conclusion": (
                "The available shadow evidence supports technical collection "
                "and operational observation only. It does not establish "
                "production readiness, client execution quality, realized "
                "capacity or live performance equivalence."
            ),
        },
        "evidence_separation": {
            "historical": {
                "status": "artifact-verified",
                "scope": "retrospective_cost_and_delay_sensitivity",
            },
            "shadow": {
                "status": "internal_operational_evidence",
                "scope": "technical_collection_and_monitoring",
            },
            "pilot": {
                "status": "not_approved_in_public_snapshot",
                "scope": "no_contractual_client_pilot_evidence",
            },
            "client_production": {
                "status": "not_established",
                "scope": "no_client_execution_or_capacity_evidence",
            },
        },
        "consolidated_assessment": {
            "status": "FAVORABLE_WITH_MATERIAL_LIMITATIONS",
            "findings": [
                (
                    "La référence artifact-verified conserve un CAGR et un "
                    "Sharpe positifs dans les 18 combinaisons publiques de "
                    "coûts et de délais."
                ),
                (
                    "À 100 bps sans délai additionnel, le CAGR historique "
                    "reste de 43,88 % et le Sharpe de 1,39."
                ),
                (
                    "À 25 bps et deux jours de délai, le CAGR historique "
                    "reste de 49,60 % et le Sharpe de 1,53."
                ),
                (
                    "Le scénario combiné de 100 bps et deux jours présente "
                    "un CAGR de 41,19 %, un Sharpe de 1,33 et un drawdown "
                    "maximal de -25,47 %."
                ),
                (
                    "Le module générique fournit une décomposition cohérente "
                    "des frais, du spread, du slippage et de l'impact."
                ),
                (
                    "Le snapshot shadow confirme 23 jours observés sur "
                    "25 jours calendaires, soit une couverture de 92 %."
                ),
            ],
            "limitations": [
                (
                    "Les sensibilités coûts-délais sont historiques et ne "
                    "constituent pas des devis d'exécution."
                ),
                (
                    "Les hypothèses de slippage et d'impact utilisées dans "
                    "la surface générique sont synthétiques."
                ),
                ("Aucune capacité réelle de Nostra AI ou d'un client n'est estimée."),
                ("Aucune donnée d'ordre client, de broker ou de lieu d'exécution n'est utilisée."),
                (
                    "Le snapshot shadow public s'arrête au 20 juillet 2026 "
                    "et ne couvre pas un mois complet."
                ),
                (
                    "L'export shadow ne contient pas de série contrôlée de "
                    "performance permettant une outcome analysis complète."
                ),
                (
                    "Aucune décision publique de readiness, d'approbation "
                    "pilote ou de production limitée n'a été prise."
                ),
                (
                    "Les résultats ne constituent ni une validation externe "
                    "indépendante, ni une prévision, ni une garantie."
                ),
            ],
        },
    }


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.titlesize": 19,
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 11,
            "axes.edgecolor": "#777777",
            "axes.labelcolor": TEXT_COLOR,
            "xtick.color": TEXT_COLOR,
            "ytick.color": TEXT_COLOR,
            "text.color": TEXT_COLOR,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def style_axis(axis: Any) -> None:
    axis.grid(
        axis="y",
        color=GRID_COLOR,
        linewidth=0.8,
        alpha=0.75,
        zorder=0,
    )
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)


def save_figure(
    figure: Any,
    path: Path,
) -> None:
    figure.savefig(
        path,
        dpi=180,
        facecolor="white",
        metadata={
            "Software": "HilmarCorp",
            "Title": path.stem,
        },
    )
    plt.close(figure)


def reference_by_delay(
    summary: dict[str, Any],
    delay: int,
) -> list[dict[str, Any]]:
    records = summary["historical_cost_delay"]["reference_records"]

    return sorted(
        [record for record in records if int(record["delay_days"]) == delay],
        key=lambda record: float(record["cost_bps"]),
    )


def plot_cost_delay_cagr(
    summary: dict[str, Any],
) -> None:
    figure, axis = plt.subplots(
        figsize=(16, 9),
        constrained_layout=True,
    )

    styles = {
        0: (NOSTRA_COLOR, "o", "0 jour"),
        1: (SECONDARY_COLOR, "s", "1 jour"),
        2: (TERTIARY_COLOR, "^", "2 jours"),
    }

    for delay in DELAY_LEVELS:
        records = reference_by_delay(summary, delay)
        color, marker, label = styles[delay]

        axis.plot(
            [float(record["cost_bps"]) for record in records],
            [float(record["cagr"]) for record in records],
            color=color,
            marker=marker,
            markersize=7,
            linewidth=2.6,
            label=label,
            zorder=3,
        )

    axis.set_title(
        "Sensibilité historique du CAGR aux coûts et aux délais",
        pad=24,
    )
    axis.set_xlabel("Coût appliqué au turnover, en points de base")
    axis.set_ylabel("CAGR historique")
    axis.set_xticks(COST_LEVELS)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))
    axis.set_ylim(0.38, 0.57)

    style_axis(axis)

    axis.legend(
        title="Délai additionnel",
        frameon=False,
        loc="upper right",
    )

    save_figure(
        figure,
        FIGURE_COST_CAGR,
    )


def plot_cost_delay_sharpe(
    summary: dict[str, Any],
) -> None:
    figure, axis = plt.subplots(
        figsize=(16, 9),
        constrained_layout=True,
    )

    styles = {
        0: (NOSTRA_COLOR, "o", "0 jour"),
        1: (SECONDARY_COLOR, "s", "1 jour"),
        2: (TERTIARY_COLOR, "^", "2 jours"),
    }

    for delay in DELAY_LEVELS:
        records = reference_by_delay(summary, delay)
        color, marker, label = styles[delay]

        axis.plot(
            [float(record["cost_bps"]) for record in records],
            [float(record["sharpe"]) for record in records],
            color=color,
            marker=marker,
            markersize=7,
            linewidth=2.6,
            label=label,
            zorder=3,
        )

    axis.axhline(
        1.0,
        color=LIGHT_COLOR,
        linewidth=1.3,
        linestyle="--",
        zorder=1,
    )

    axis.set_title(
        "Sensibilité historique du Sharpe aux coûts et aux délais",
        pad=24,
    )
    axis.set_xlabel("Coût appliqué au turnover, en points de base")
    axis.set_ylabel("Sharpe annualisé")
    axis.set_xticks(COST_LEVELS)
    axis.set_ylim(1.20, 1.72)

    style_axis(axis)

    axis.legend(
        title="Délai additionnel",
        frameon=False,
        loc="upper right",
    )

    save_figure(
        figure,
        FIGURE_COST_SHARPE,
    )


def plot_synthetic_execution_surface(
    summary: dict[str, Any],
) -> None:
    records = summary["generic_execution_framework"]["synthetic_execution_surface"]

    figure, axis = plt.subplots(
        figsize=(16, 9),
        constrained_layout=True,
    )

    styles = {
        0.02: (NOSTRA_COLOR, "o", "Volatilité quotidienne 2 %"),
        0.04: (SECONDARY_COLOR, "s", "Volatilité quotidienne 4 %"),
        0.08: (TERTIARY_COLOR, "^", "Volatilité quotidienne 8 %"),
    }

    for volatility in SYNTHETIC_VOLATILITIES:
        selected = sorted(
            [
                record
                for record in records
                if (
                    close(float(record["daily_volatility"]), volatility)
                    and close(float(record["slippage_bps"]), 5.0)
                )
            ],
            key=lambda record: float(record["participation_rate"]),
        )

        color, marker, label = styles[volatility]

        axis.plot(
            [float(record["participation_rate"]) * 100 for record in selected],
            [float(record["total_cost_bps"]) for record in selected],
            color=color,
            marker=marker,
            markersize=7,
            linewidth=2.6,
            label=label,
            zorder=3,
        )

    axis.set_title(
        "Surface synthétique de coût d'exécution",
        pad=24,
    )
    axis.set_xlabel("Taux de participation au volume quotidien")
    axis.set_ylabel("Coût total synthétique, en points de base")
    axis.xaxis.set_major_formatter(PercentFormatter(100.0))
    axis.set_xlim(0.0, 10.5)

    style_axis(axis)

    axis.legend(
        frameon=False,
        loc="upper left",
    )

    save_figure(
        figure,
        FIGURE_EXECUTION_SURFACE,
    )


def plot_synthetic_capacity(
    summary: dict[str, Any],
) -> None:
    records = summary["generic_execution_framework"]["synthetic_capacity_records"]

    figure, axis = plt.subplots(
        figsize=(16, 9),
        constrained_layout=True,
    )

    styles = {
        0.02: (NOSTRA_COLOR, "o", "Volatilité quotidienne 2 %"),
        0.04: (SECONDARY_COLOR, "s", "Volatilité quotidienne 4 %"),
        0.08: (TERTIARY_COLOR, "^", "Volatilité quotidienne 8 %"),
    }

    for volatility in SYNTHETIC_VOLATILITIES:
        selected = sorted(
            [record for record in records if close(float(record["daily_volatility"]), volatility)],
            key=lambda record: float(record["expected_gross_edge_bps"]),
        )

        color, marker, label = styles[volatility]

        axis.plot(
            [float(record["expected_gross_edge_bps"]) for record in selected],
            [float(record["maximum_notional"]) / 1_000_000 for record in selected],
            color=color,
            marker=marker,
            markersize=7,
            linewidth=2.6,
            label=label,
            zorder=3,
        )

    axis.set_title(
        "Notionnel synthétique compatible avec les contraintes du modèle",
        pad=24,
    )
    axis.set_xlabel("Edge brut hypothétique, en points de base")
    axis.set_ylabel("Notionnel synthétique maximal, en millions")
    axis.set_xticks(SYNTHETIC_EDGE_LEVELS)
    axis.set_ylim(-0.2, 10.8)

    style_axis(axis)

    axis.legend(
        frameon=False,
        loc="lower right",
    )

    save_figure(
        figure,
        FIGURE_CAPACITY,
    )


def write_markdown(
    summary: dict[str, Any],
) -> None:
    historical = summary["historical_cost_delay"]
    selected = historical["selected_reference_scenarios"]
    framework = summary["generic_execution_framework"]
    shadow = summary["shadow_monitoring"]
    capacity_records = framework["synthetic_capacity_records"]

    scenario_rows = [
        (
            "Référence historique",
            selected["baseline_25bps_0day"],
        ),
        (
            "Coût élevé",
            selected["high_cost_100bps_0day"],
        ),
        (
            "Délai de deux jours",
            selected["delay_25bps_2days"],
        ),
        (
            "Stress combiné",
            selected["combined_100bps_2days"],
        ),
    ]

    capacity_four_percent = {
        float(record["expected_gross_edge_bps"]): record
        for record in capacity_records
        if close(float(record["daily_volatility"]), 0.04)
    }

    lines = [
        "# Partie IX - Exécution, capacité et shadow",
        "",
        "## Tableau 9.1",
        "",
        "### Sensibilité historique sélectionnée aux coûts et aux délais",
        "",
        ("| Scénario | Coût | Délai | CAGR | Sharpe | Drawdown maximal | Equity finale |"),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for label, record in scenario_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    f"{format_number(float(record['cost_bps']), 0)} bps",
                    f"{int(record['delay_days'])} jour(s)",
                    format_percent(float(record["cagr"])),
                    format_number(float(record["sharpe"]), 2),
                    format_percent(float(record["maximum_drawdown"])),
                    format_number(float(record["final_equity"]), 2),
                ]
            )
            + " |"
        )

    assumptions = framework["synthetic_assumptions"]

    lines.extend(
        [
            "",
            "## Tableau 9.2",
            "",
            "### Hypothèses du cadre générique synthétique",
            "",
            "| Hypothèse | Valeur | Statut |",
            "|---|---:|---|",
            (f"| Frais | {format_number(float(assumptions['fee_bps']))} bps | Illustratif |"),
            (
                "| Demi-spread | "
                f"{format_number(float(assumptions['half_spread_bps']))} bps "
                "| Illustratif |"
            ),
            (
                "| Slippage central | "
                f"{format_number(float(assumptions['slippage_bps']))} bps "
                "| Illustratif |"
            ),
            (
                "| Coefficient d'impact | "
                f"{format_number(float(assumptions['impact_coefficient_bps']))} bps "
                "| Illustratif |"
            ),
            (
                "| Exposant d'impact | "
                f"{format_number(float(assumptions['impact_exponent']), 2)} "
                "| Forme racine carrée |"
            ),
            (
                "| Participation de référence | "
                f"{format_percent(float(assumptions['reference_participation_rate']))} "
                "| Illustratif |"
            ),
            (
                "| Limite de participation | "
                f"{format_percent(float(assumptions['maximum_participation_rate']))} "
                "| Illustratif |"
            ),
            (
                "| Volume quotidien | "
                f"{format_number(float(assumptions['daily_volume_notional']) / 1_000_000, 0)} "
                "millions | Illustratif |"
            ),
            "",
            (
                "Le coût total synthétique est la somme des frais, du "
                "demi-spread, du slippage et de l'impact de marché. "
                "L'impact dépend du taux de participation et de la "
                "volatilité quotidienne."
            ),
            "",
            "## Tableau 9.3",
            "",
            ("### Notionnel synthétique sous volatilité quotidienne illustrative de 4 %"),
            "",
            (
                "| Edge brut hypothétique | Notionnel maximal | "
                "Participation | Coût estimé | Contrainte active |"
            ),
            "|---:|---:|---:|---:|---|",
        ]
    )

    for edge in (8.0, 12.0, 18.0, 25.0, 50.0, 100.0):
        record = capacity_four_percent[edge]

        lines.append(
            "| "
            + " | ".join(
                [
                    f"{format_number(edge, 0)} bps",
                    (f"{format_number(float(record['maximum_notional']) / 1_000_000, 3)} millions"),
                    format_percent(float(record["participation_rate"])),
                    f"{format_number(float(record['estimated_cost_bps']))} bps",
                    str(record["binding_constraint"]),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            (
                "Ces notionnels sont des sorties d'un exemple synthétique. "
                "Ils ne représentent ni Nostra AI, ni un client, ni un broker, "
                "ni un lieu d'exécution. Cette grille n'est pas une estimation "
                "de capacité réelle."
            ),
            "",
            "## Tableau 9.4",
            "",
            "### Snapshot public du monitoring shadow",
            "",
            "| Indicateur | Valeur |",
            "|---|---:|",
            f"| Première observation | {shadow['first_observed_day']} |",
            f"| Dernière observation | {shadow['last_observed_day']} |",
            f"| Jours calendaires | {shadow['calendar_days']} |",
            f"| Jours observés | {shadow['observed_days']} |",
            f"| Jours manquants | {shadow['missing_day_count']} |",
            f"| Couverture | {format_percent(float(shadow['coverage_ratio']), 0)} |",
            (
                "| Collecte technique complète | "
                f"{'Oui' if shadow['technical_collection_complete'] else 'Non'} |"
            ),
            (
                "| Approbation humaine requise | "
                f"{'Oui' if shadow['human_approval_required'] else 'Non'} |"
            ),
            (
                "| Approbation pilote ou production limitée | "
                f"{'Oui' if shadow['pilot_or_limited_production_approval'] else 'Non'} |"
            ),
            (f"| Décision de readiness production | {shadow['production_readiness_decision']} |"),
            "",
            "## Lecture consolidée",
            "",
            (
                "La grille historique indique que la performance demeure "
                "positive dans toutes les combinaisons publiques de coûts et "
                "de délais, mais qu'elle se dégrade à mesure que le coût ou le "
                "délai augmente. Le cadre générique d'exécution démontre une "
                "architecture méthodologique cohérente pour les frais, le "
                "spread, le slippage, l'impact et les contraintes de capacité. "
                "Il n'est pas calibré sur des exécutions réelles de Nostra AI "
                "ou d'un client."
            ),
            "",
            (
                "Le monitoring shadow constitue une preuve opérationnelle "
                "interne limitée. Le snapshot public couvre 23 jours observés "
                "sur 25 jours calendaires et ne contient pas une série de "
                "performance permettant une outcome analysis complète. "
                "Il ne matérialise aucune approbation pilote ou production."
            ),
            "",
            "### Limites",
            "",
        ]
    )

    for limitation in summary["consolidated_assessment"]["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            (
                "Conclusion contrôlée : la robustesse historique aux coûts et "
                "aux délais est favorable dans la grille publique examinée. "
                "La capacité réelle, la qualité d'exécution client et "
                "l'équivalence entre historique et shadow ne sont pas "
                "démontrées."
            ),
            "",
        ]
    )

    MARKDOWN_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_manifest_and_checksums() -> None:
    controlled_paths = [
        SUMMARY_PATH,
        MARKDOWN_PATH,
        GENERATOR_PATH,
        *FIGURE_PATHS,
    ]

    records = []

    for path in sorted(
        controlled_paths,
        key=lambda item: item.relative_to(ROOT).as_posix(),
    ):
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    manifest = {
        "schema_version": 1,
        "package": "part_ix_execution_capacity_shadow_report_support",
        "model": MODEL,
        "source_release": SOURCE_RELEASE,
        "files": records,
    }

    write_json(
        MANIFEST_PATH,
        manifest,
    )

    CHECKSUMS_PATH.write_text(
        "".join(f"{record['sha256']}  {record['path']}\n" for record in records),
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

    sources = load_sources()
    summary = build_summary(sources)

    write_json(
        SUMMARY_PATH,
        summary,
    )
    write_markdown(summary)

    configure_plotting()
    plot_cost_delay_cagr(summary)
    plot_cost_delay_sharpe(summary)
    plot_synthetic_execution_surface(summary)
    plot_synthetic_capacity(summary)

    write_manifest_and_checksums()

    print("PASS_PART_IX_EXECUTION_CAPACITY_SHADOW_SUPPORT_READY")
    print(f"Résumé : {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Tableaux : {MARKDOWN_PATH.relative_to(ROOT)}")
    print(f"Figures : {len(FIGURE_PATHS)}")
    print(f"Sources gelées réconciliées : {len(SOURCE_FILES)}")


if __name__ == "__main__":
    main()
