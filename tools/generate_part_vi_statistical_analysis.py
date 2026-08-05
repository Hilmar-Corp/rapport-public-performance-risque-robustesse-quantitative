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
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"

SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_vi"
FIGURES_DIR = ROOT / "docs" / "figures"
TABLES_DIR = ROOT / "docs" / "tables"

SUMMARY_PATH = SUPPORT_DIR / "part_vi_statistical_summary.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = TABLES_DIR / "part_vi_statistical_results.md"

FIGURE_PBO = FIGURES_DIR / "figure_6_1_pbo_aggregate_sensitivity.png"
FIGURE_PVALUES = FIGURES_DIR / "figure_6_2_benchmark_bootstrap_pvalues.png"
FIGURE_INTERVALS = FIGURES_DIR / "figure_6_3_benchmark_bootstrap_intervals.png"
FIGURE_HAC = FIGURES_DIR / "figure_6_4_hac_sharpe_sensitivity.png"
FIGURE_BOOTSTRAP = FIGURES_DIR / "figure_6_5_circular_bootstrap_intervals.png"

SOURCE_FILES = {
    "probabilistic_sharpe_ratio": "probabilistic_sharpe_ratio.json",
    "deflated_sharpe_ratio": "deflated_sharpe_ratio.json",
    "multiple_testing": "multiple_testing.json",
    "backtest_overfitting": "backtest_overfitting.json",
    "moving_block_bootstrap": "moving_block_bootstrap.json",
    "temporal_dependence_sharpe": "temporal_dependence_sharpe.json",
}

SOURCE_SHA256 = {
    "probabilistic_sharpe_ratio": (
        "b6963cf16736d0bd147865061180daab3c6a7b4d63f28f8802d7e8cd49deb456"
    ),
    "deflated_sharpe_ratio": ("6ab226e0cdd0ecf7c90c72a3bfa6b2b969a369d1691d5ab0080ee3d53374c810"),
    "multiple_testing": ("78f06233f1c24a5bc930cd1fd287323f4c2c05684dad7b187fd5f352f478504f"),
    "backtest_overfitting": ("033ad1e50f70b0dd995e618a47f65d98756a794c9b68e5d3e75926abda0844e7"),
    "moving_block_bootstrap": ("a76215334c29ecb35cb840c30f22e0e7298624096762786cf88ecb935ac8b94a"),
    "temporal_dependence_sharpe": (
        "6cfc6c79242d5a06dbb56065f2ba06bb8f91852fb2e847dc759d59478c72be7b"
    ),
}

EXPECTED_SECTIONS = {
    "probabilistic_sharpe_ratio": "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio": "deflated_sharpe_ratio",
    "multiple_testing": "multiple_testing",
    "backtest_overfitting": "backtest_overfitting",
    "moving_block_bootstrap": "moving_block_bootstrap",
    "temporal_dependence_sharpe": "temporal_dependence_sharpe",
}

EXPECTED_BENCHMARKS = {
    "BUY_AND_HOLD",
    "FIXED_50",
    "HMM_3_STATE_WALKFORWARD",
    "MA_50_200",
    "MOMENTUM_180",
    "MOMENTUM_270",
    "MOMENTUM_30",
    "MOMENTUM_60",
    "MOMENTUM_90",
    "VOL_TARGET_14",
    "VOL_TARGET_30",
}

BENCHMARK_LABELS = {
    "BUY_AND_HOLD": "Bitcoin passif",
    "FIXED_50": "Allocation fixe 50 %",
    "HMM_3_STATE_WALKFORWARD": "HMM 3 états",
    "MA_50_200": "Moyennes mobiles 50/200",
    "MOMENTUM_180": "Momentum 180 jours",
    "MOMENTUM_270": "Momentum 270 jours",
    "MOMENTUM_30": "Momentum 30 jours",
    "MOMENTUM_60": "Momentum 60 jours",
    "MOMENTUM_90": "Momentum 90 jours",
    "VOL_TARGET_14": "Ciblage volatilité 14 jours",
    "VOL_TARGET_30": "Ciblage volatilité 30 jours",
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
    tolerance: float = 1e-14,
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
            (f"Empreinte source non conforme pour {filename}: {observed_sha}"),
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

        data = payload.get("data")

        require(
            isinstance(data, dict),
            f"Bloc data absent pour {filename}.",
        )

        require(
            data.get("verification_level") == "artifact-verified",
            f"Niveau de vérification non conforme pour {filename}.",
        )

        payloads[name] = payload

    return payloads


def validate_sources(
    payloads: dict[str, dict[str, Any]],
) -> None:
    psr = payloads["probabilistic_sharpe_ratio"]["data"]
    dsr = payloads["deflated_sharpe_ratio"]["data"]
    multiple = payloads["multiple_testing"]["data"]
    pbo = payloads["backtest_overfitting"]["data"]
    bootstrap = payloads["moving_block_bootstrap"]["data"]
    temporal = payloads["temporal_dependence_sharpe"]["data"]

    require(
        psr["observations"] == OBSERVATIONS,
        "Nombre d'observations PSR non conforme.",
    )
    require(
        psr["annualization"] == ANNUALIZATION,
        "Annualisation PSR non conforme.",
    )
    require(
        close(
            float(psr["probability"]),
            0.999967305016425,
        ),
        "Probabilité PSR non conforme.",
    )
    require(
        close(
            float(psr["observed_annualized_sharpe"]),
            1.587687113383514,
        ),
        "Sharpe observé PSR non conforme.",
    )

    require(
        dsr["observations"] == OBSERVATIONS,
        "Nombre d'observations DSR non conforme.",
    )
    require(
        dsr["annualization"] == ANNUALIZATION,
        "Annualisation DSR non conforme.",
    )
    require(
        dsr["trial_count"] == 15,
        "Nombre d'essais DSR non conforme.",
    )
    require(
        close(
            float(dsr["probability"]),
            0.99996656687852,
        ),
        "Probabilité DSR non conforme.",
    )

    require(
        multiple["observations"] == OBSERVATIONS,
        "Nombre d'observations des tests multiples non conforme.",
    )
    require(
        multiple["candidate_count"] == 15,
        "Nombre de candidats des tests multiples non conforme.",
    )
    require(
        multiple["repetitions"] == 2000,
        "Nombre de répétitions des tests multiples non conforme.",
    )
    require(
        multiple["block_size"] == 21,
        "Taille de bloc des tests multiples non conforme.",
    )
    require(
        float(multiple["white_reality_check"]["reported_p_value"]) == 0.0,
        "P-value White Reality Check non conforme.",
    )
    require(
        float(multiple["hansen_spa"]["reported_p_value"]) == 0.0,
        "P-value Hansen SPA non conforme.",
    )

    require(
        pbo["observations"] == OBSERVATIONS,
        "Nombre d'observations PBO non conforme.",
    )
    require(
        pbo["blocks"] == 8,
        "Nombre de blocs CSCV non conforme.",
    )
    require(
        pbo["candidate_count"] == 15,
        "Nombre de candidats CSCV non conforme.",
    )
    require(
        pbo["tested_setting_count"] == 4,
        "Nombre de configurations PBO non conforme.",
    )
    require(
        pbo["combinations_per_setting"] == 70,
        "Nombre de combinaisons CSCV non conforme.",
    )
    require(
        pbo["all_combinations_completed"] is True,
        "Toutes les combinaisons CSCV doivent être terminées.",
    )
    require(
        pbo["results_below_0_20"] == 3,
        "Nombre de résultats PBO sous 20 % non conforme.",
    )
    require(
        0.0
        <= float(pbo["pbo_minimum"])
        <= float(pbo["pbo_median"])
        <= float(pbo["pbo_maximum"])
        <= 1.0,
        "Ordre des agrégats PBO non conforme.",
    )
    require(
        float(pbo["pbo_minimum"]) <= float(pbo["pbo_mean"]) <= float(pbo["pbo_maximum"]),
        "Moyenne PBO hors de la plage publiée.",
    )

    records = bootstrap["records"]

    require(
        isinstance(records, list),
        "Les enregistrements bootstrap doivent former une liste.",
    )
    require(
        len(records) == 11,
        "Le bootstrap doit contenir onze références.",
    )
    require(
        {str(record["benchmark"]) for record in records} == EXPECTED_BENCHMARKS,
        "Ensemble des références bootstrap non conforme.",
    )
    require(
        bootstrap["benchmark_count"] == 11,
        "Nombre de références bootstrap non conforme.",
    )
    require(
        bootstrap["positive_cagr_differences"] == 11,
        "Les onze écarts de CAGR doivent être positifs.",
    )
    require(
        bootstrap["significant_at_5_percent"] == 2,
        "Deux comparaisons bootstrap doivent être significatives.",
    )

    official_significant = []

    for record in records:
        p_value = float(record["one_sided_p_value"])
        lower = float(record["ci95_lower_annualized_log"])
        official = bool(record["significant_compounded_outperformance"])
        expected_official = p_value < 0.05 and lower > 0.0

        require(
            official is expected_official,
            (f"Verdict bootstrap non conforme pour {record['benchmark']}."),
        )
        require(
            float(record["cagr_difference"]) > 0.0,
            (f"Écart de CAGR non positif pour {record['benchmark']}."),
        )

        if official:
            official_significant.append(str(record["benchmark"]))

    require(
        official_significant
        == [
            "FIXED_50",
            "HMM_3_STATE_WALKFORWARD",
        ],
        "Liste des comparaisons significatives non conforme.",
    )

    require(
        temporal["observations"] == OBSERVATIONS,
        "Nombre d'observations temporelles non conforme.",
    )
    require(
        temporal["annualization"] == ANNUALIZATION,
        "Annualisation temporelle non conforme.",
    )
    require(
        temporal["canonical_hac_lag_count"] == 21,
        "Retard HAC canonique non conforme.",
    )
    require(
        close(
            float(temporal["canonical_hac_adjusted_annualized_sharpe"]),
            1.4931827873589063,
        ),
        "Sharpe HAC canonique non conforme.",
    )
    require(
        temporal["decision_status"] == "PASS_WITH_OBSERVATION",
        "Décision temporelle non conforme.",
    )

    hac_records = temporal["hac_sensitivity_records"]

    require(
        [int(record["lag_count"]) for record in hac_records] == [5, 7, 10, 21, 30, 60],
        "Retards HAC non conformes.",
    )

    bootstrap_records = temporal["bootstrap_sensitivity_records"]

    require(
        [int(record["block_size"]) for record in bootstrap_records] == [5, 10, 21, 30, 60],
        "Tailles de bloc du bootstrap circulaire non conformes.",
    )
    require(
        all(float(record["interval_lower"]) > 0.0 for record in bootstrap_records),
        "Toutes les bornes basses bootstrap doivent être positives.",
    )
    require(
        temporal["diagnostics"]["all_bootstrap_lower_bounds_positive"] is True,
        "Diagnostic des bornes bootstrap non conforme.",
    )


def format_number(
    value: float,
    decimals: int = 3,
) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def format_percent(
    value: float,
    decimals: int = 2,
) -> str:
    return f"{value * 100:.{decimals}f}".replace(".", ",") + " %"


def format_probability(
    value: float,
    decimals: int = 4,
) -> str:
    if value == 0.0:
        return "0,0000 %*"

    return format_percent(
        value,
        decimals=decimals,
    )


def format_scientific(
    value: float,
) -> str:
    if value == 0.0:
        return "0"

    if abs(value) < 0.0001:
        return f"{value:.2e}".replace(".", ",")

    return format_number(
        value,
        decimals=6,
    )


def benchmark_label(name: str) -> str:
    return BENCHMARK_LABELS.get(
        name,
        name,
    )


def official_color(
    record: dict[str, Any],
) -> str:
    if bool(record["significant_compounded_outperformance"]):
        return NOSTRA_COLOR

    if float(record["one_sided_p_value"]) < 0.05:
        return CONDITIONAL_COLOR

    return NEUTRAL_COLOR


def style_axis(
    axis: plt.Axes,
    *,
    grid_axis: str = "y",
) -> None:
    axis.grid(
        axis=grid_axis,
        color=GRID_COLOR,
        linewidth=0.8,
        alpha=0.8,
        zorder=0,
    )

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_color(AXIS_COLOR)
    axis.spines["bottom"].set_color(AXIS_COLOR)

    axis.tick_params(
        colors=TEXT_COLOR,
        labelsize=9,
    )

    axis.xaxis.label.set_color(TEXT_COLOR)
    axis.yaxis.label.set_color(TEXT_COLOR)


def save_figure(
    figure: plt.Figure,
    path: Path,
) -> None:
    figure.tight_layout()

    figure.savefig(
        path,
        dpi=320,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Software": ("HilmarCorp controlled Part VI report support")},
    )

    plt.close(figure)


def generate_pbo_figure(
    pbo: dict[str, Any],
) -> None:
    labels = [
        "Minimum",
        "Médiane",
        "Moyenne",
        "Maximum",
    ]

    values = [
        float(pbo["pbo_minimum"]),
        float(pbo["pbo_median"]),
        float(pbo["pbo_mean"]),
        float(pbo["pbo_maximum"]),
    ]

    figure, axis = plt.subplots(
        figsize=(10.5, 5.6),
    )

    bars = axis.bar(
        labels,
        values,
        width=0.56,
        color=[
            LIGHT_NEUTRAL_COLOR,
            NOSTRA_COLOR,
            NOSTRA_COLOR,
            NEUTRAL_COLOR,
        ],
        zorder=3,
    )

    axis.axhline(
        0.20,
        color=CONDITIONAL_COLOR,
        linestyle="--",
        linewidth=1.3,
        label="Seuil indicatif de 20 %",
        zorder=2,
    )

    for bar, value in zip(
        bars,
        values,
        strict=True,
    ):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.006,
            format_percent(
                value,
                decimals=1,
            ),
            ha="center",
            va="bottom",
            fontsize=9,
            color=TEXT_COLOR,
        )

    axis.set_ylabel("Probabilité de surapprentissage du backtest")
    axis.set_ylim(
        0.0,
        max(values) + 0.045,
    )
    axis.yaxis.set_major_formatter(
        PercentFormatter(
            xmax=1.0,
            decimals=0,
        )
    )

    axis.legend(
        frameon=False,
        loc="upper left",
        fontsize=9,
    )

    style_axis(
        axis,
        grid_axis="y",
    )

    save_figure(
        figure,
        FIGURE_PBO,
    )


def generate_pvalue_figure(
    bootstrap: dict[str, Any],
) -> None:
    records = sorted(
        bootstrap["records"],
        key=lambda record: float(record["one_sided_p_value"]),
        reverse=True,
    )

    labels = [benchmark_label(str(record["benchmark"])) for record in records]

    values = [float(record["one_sided_p_value"]) for record in records]

    colors = [official_color(record) for record in records]

    positions = list(range(len(records)))

    figure, axis = plt.subplots(
        figsize=(11.5, 7.0),
    )

    axis.scatter(
        values,
        positions,
        color=colors,
        s=54,
        zorder=3,
    )

    axis.axvline(
        0.05,
        color=CONDITIONAL_COLOR,
        linestyle="--",
        linewidth=1.3,
        zorder=2,
    )

    for position, value in zip(
        positions,
        values,
        strict=True,
    ):
        axis.text(
            value + 0.006,
            position,
            format_percent(
                value,
                decimals=2,
            ),
            va="center",
            fontsize=8.5,
            color=TEXT_COLOR,
        )

    axis.set_yticks(
        positions,
        labels,
    )
    axis.set_xlabel("P-value unilatérale")
    axis.set_xlim(
        0.0,
        max(values) + 0.055,
    )
    axis.xaxis.set_major_formatter(
        PercentFormatter(
            xmax=1.0,
            decimals=0,
        )
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            color=NOSTRA_COLOR,
            label="Verdict officiel significatif",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            color=CONDITIONAL_COLOR,
            label=("P-value < 5 %, mais intervalle recoupant zéro"),
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            color=NEUTRAL_COLOR,
            label="Non significatif",
        ),
    ]

    axis.legend(
        handles=legend_handles,
        frameon=False,
        loc="upper right",
        fontsize=8.5,
    )

    style_axis(
        axis,
        grid_axis="x",
    )

    save_figure(
        figure,
        FIGURE_PVALUES,
    )


def generate_interval_figure(
    bootstrap: dict[str, Any],
) -> None:
    records = sorted(
        bootstrap["records"],
        key=lambda record: float(record["annualized_log_outperformance"]),
    )

    positions = list(range(len(records)))

    labels = [benchmark_label(str(record["benchmark"])) for record in records]

    figure, axis = plt.subplots(
        figsize=(11.5, 7.2),
    )

    axis.axvline(
        0.0,
        color=AXIS_COLOR,
        linestyle="-",
        linewidth=1.0,
        zorder=1,
    )

    for position, record in zip(
        positions,
        records,
        strict=True,
    ):
        point = float(record["annualized_log_outperformance"])
        lower = float(record["ci95_lower_annualized_log"])
        upper = float(record["ci95_upper_annualized_log"])

        axis.errorbar(
            point,
            position,
            xerr=[
                [point - lower],
                [upper - point],
            ],
            fmt="o",
            color=official_color(record),
            ecolor=official_color(record),
            elinewidth=1.8,
            capsize=3.5,
            markersize=5.5,
            zorder=3,
        )

    axis.set_yticks(
        positions,
        labels,
    )
    axis.set_xlabel("Surperformance logarithmique annualisée")
    axis.xaxis.set_major_formatter(
        PercentFormatter(
            xmax=1.0,
            decimals=0,
        )
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="-",
            color=NOSTRA_COLOR,
            label="Verdict officiel significatif",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="-",
            color=CONDITIONAL_COLOR,
            label=("P-value < 5 %, borne basse non positive"),
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="-",
            color=NEUTRAL_COLOR,
            label="Non significatif",
        ),
    ]

    axis.legend(
        handles=legend_handles,
        frameon=False,
        loc="lower right",
        fontsize=8.5,
    )

    style_axis(
        axis,
        grid_axis="x",
    )

    save_figure(
        figure,
        FIGURE_INTERVALS,
    )


def generate_hac_figure(
    temporal: dict[str, Any],
) -> None:
    records = temporal["hac_sensitivity_records"]

    lags = [int(record["lag_count"]) for record in records]

    sharpes = [float(record["hac_adjusted_annualized_sharpe"]) for record in records]

    conventional = float(temporal["conventional_annualized_sharpe"])

    canonical_lag = int(temporal["canonical_hac_lag_count"])

    canonical_sharpe = float(temporal["canonical_hac_adjusted_annualized_sharpe"])

    positions = list(range(len(lags)))
    canonical_position = lags.index(canonical_lag)

    figure, axis = plt.subplots(
        figsize=(10.5, 5.6),
    )

    axis.plot(
        positions,
        sharpes,
        color=NOSTRA_COLOR,
        linewidth=2.0,
        marker="o",
        markersize=5.5,
        zorder=3,
    )

    axis.axhline(
        conventional,
        color=NEUTRAL_COLOR,
        linestyle="--",
        linewidth=1.3,
        label=(f"Sharpe conventionnel {format_number(conventional, 2)}"),
        zorder=2,
    )

    axis.scatter(
        [canonical_position],
        [canonical_sharpe],
        color=CONDITIONAL_COLOR,
        s=74,
        zorder=4,
        label=(f"Choix canonique, {canonical_lag} retards"),
    )

    axis.set_xlabel("Configurations de retards Newey-West testées")
    axis.set_ylabel("Ratio de Sharpe annualisé")
    axis.set_xticks(
        positions,
        [str(lag) for lag in lags],
    )
    axis.set_ylim(
        min(sharpes) - 0.035,
        max(max(sharpes), conventional) + 0.035,
    )

    axis.legend(
        frameon=False,
        loc="lower left",
        fontsize=9,
    )

    style_axis(
        axis,
        grid_axis="y",
    )

    save_figure(
        figure,
        FIGURE_HAC,
    )


def generate_circular_bootstrap_figure(
    temporal: dict[str, Any],
) -> None:
    records = temporal["bootstrap_sensitivity_records"]

    blocks = [int(record["block_size"]) for record in records]

    medians = [float(record["bootstrap_median"]) for record in records]

    lowers = [float(record["interval_lower"]) for record in records]

    uppers = [float(record["interval_upper"]) for record in records]

    conventional = float(temporal["conventional_annualized_sharpe"])

    positions = list(range(len(blocks)))

    figure, axis = plt.subplots(
        figsize=(10.5, 5.8),
    )

    for position, block, median, lower, upper in zip(
        positions,
        blocks,
        medians,
        lowers,
        uppers,
        strict=True,
    ):
        color = CONDITIONAL_COLOR if block == 21 else NOSTRA_COLOR

        axis.errorbar(
            position,
            median,
            yerr=[
                [median - lower],
                [upper - median],
            ],
            fmt="o",
            color=color,
            ecolor=color,
            elinewidth=1.8,
            capsize=4.0,
            markersize=6.0,
            zorder=3,
        )

    axis.axhline(
        0.0,
        color=AXIS_COLOR,
        linewidth=1.0,
        zorder=1,
    )

    axis.axhline(
        conventional,
        color=NEUTRAL_COLOR,
        linestyle="--",
        linewidth=1.3,
        label=(f"Sharpe conventionnel {format_number(conventional, 2)}"),
        zorder=2,
    )

    axis.set_xlabel("Tailles de bloc circulaire testées")
    axis.set_ylabel("Ratio de Sharpe bootstrap (médiane et intervalle à 95 %)")
    axis.set_xticks(
        positions,
        [str(block) for block in blocks],
    )
    axis.set_ylim(
        0.0,
        max(uppers) + 0.14,
    )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="-",
            color=NOSTRA_COLOR,
            label="Configurations de sensibilité",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="-",
            color=CONDITIONAL_COLOR,
            label="Taille canonique de 21",
        ),
        Line2D(
            [0],
            [0],
            linestyle="--",
            color=NEUTRAL_COLOR,
            label=(f"Sharpe conventionnel {format_number(conventional, 2)}"),
        ),
    ]

    axis.legend(
        handles=legend_handles,
        frameon=False,
        loc="lower right",
        fontsize=8.5,
    )

    style_axis(
        axis,
        grid_axis="y",
    )

    save_figure(
        figure,
        FIGURE_BOOTSTRAP,
    )


def build_summary(
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    psr = payloads["probabilistic_sharpe_ratio"]["data"]
    dsr = payloads["deflated_sharpe_ratio"]["data"]
    multiple = payloads["multiple_testing"]["data"]
    pbo = payloads["backtest_overfitting"]["data"]
    bootstrap = payloads["moving_block_bootstrap"]["data"]
    temporal = payloads["temporal_dependence_sharpe"]["data"]

    records = bootstrap["records"]

    official_significant = [
        str(record["benchmark"])
        for record in records
        if bool(record["significant_compounded_outperformance"])
    ]

    threshold_only = [
        str(record["benchmark"])
        for record in records
        if float(record["one_sided_p_value"]) < 0.05
        and not bool(record["significant_compounded_outperformance"])
    ]

    source_files = []

    for name, filename in SOURCE_FILES.items():
        path = SOURCE_DIR / filename

        source_files.append(
            {
                "section": name,
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    return {
        "schema_version": 1,
        "package": "part_vi_statistical_report_support",
        "model": "Nostra AI V5.246",
        "source_release": "v0.3.0",
        "period": {
            "start": "2020-05-14",
            "end": "2026-06-02",
            "observations": OBSERVATIONS,
            "annualization": ANNUALIZATION,
        },
        "status": (
            "Transformation contrôlée des six agrégats "
            "statistiques publics gelés de la release v0.3.0."
        ),
        "source_files": source_files,
        "probabilistic_sharpe_ratio": psr,
        "deflated_sharpe_ratio": dsr,
        "multiple_testing": multiple,
        "backtest_overfitting": pbo,
        "moving_block_bootstrap": bootstrap,
        "temporal_dependence_sharpe": temporal,
        "consolidated_reading": {
            "psr_probability": float(psr["probability"]),
            "dsr_probability": float(dsr["probability"]),
            "pbo_range": {
                "minimum": float(pbo["pbo_minimum"]),
                "median": float(pbo["pbo_median"]),
                "mean": float(pbo["pbo_mean"]),
                "maximum": float(pbo["pbo_maximum"]),
            },
            "pbo_settings_below_0_20": int(pbo["results_below_0_20"]),
            "pbo_tested_setting_count": int(pbo["tested_setting_count"]),
            "positive_benchmark_cagr_differences": int(bootstrap["positive_cagr_differences"]),
            "official_significant_benchmarks": (official_significant),
            "p_below_0_05_but_interval_crosses_zero": (threshold_only),
            "conventional_annualized_sharpe": float(temporal["conventional_annualized_sharpe"]),
            "canonical_hac_adjusted_sharpe": float(
                temporal["canonical_hac_adjusted_annualized_sharpe"]
            ),
            "canonical_hac_lag_count": int(temporal["canonical_hac_lag_count"]),
            "all_circular_bootstrap_lower_bounds_positive": (
                bool(temporal["diagnostics"]["all_bootstrap_lower_bounds_positive"])
            ),
            "decision_status": str(temporal["decision_status"]),
        },
    }


def write_summary(
    summary: dict[str, Any],
) -> None:
    SUMMARY_PATH.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_markdown(
    payloads: dict[str, dict[str, Any]],
) -> None:
    psr = payloads["probabilistic_sharpe_ratio"]["data"]
    dsr = payloads["deflated_sharpe_ratio"]["data"]
    multiple = payloads["multiple_testing"]["data"]
    pbo = payloads["backtest_overfitting"]["data"]
    bootstrap = payloads["moving_block_bootstrap"]["data"]
    temporal = payloads["temporal_dependence_sharpe"]["data"]

    lines = [
        "# Résultats statistiques institutionnels de la Partie VI",
        "",
        ("Source contrôlée : six agrégats publics artifact-verified de la release v0.3.0."),
        "",
        "## Tableau 6.1 - Probabilistic Sharpe Ratio et Deflated Sharpe Ratio",
        "",
        ("| Mesure | PSR | DSR |"),
        "|---|---:|---:|",
        (f"| Observations | {psr['observations']} | {dsr['observations']} |"),
        (f"| Annualisation | {psr['annualization']} | {dsr['annualization']} |"),
        (
            "| Sharpe observé | "
            f"{format_number(float(psr['observed_annualized_sharpe']), 4)} "
            "| n/a |"
        ),
        (
            "| Maximum de Sharpe attendu | n/a | "
            f"{format_number(float(dsr['expected_maximum_sharpe']), 6)} |"
        ),
        (f"| Nombre d'essais | n/a | {dsr['trial_count']} |"),
        (
            "| Skewness | "
            f"{format_number(float(psr['skewness']), 4)} | "
            f"{format_number(float(dsr['skewness']), 4)} |"
        ),
        (
            "| Kurtosis de Pearson | "
            f"{format_number(float(psr['pearson_kurtosis']), 4)} | "
            f"{format_number(float(dsr['pearson_kurtosis']), 4)} |"
        ),
        (
            "| Statistique de test | "
            f"{format_number(float(psr['test_statistic']), 4)} | "
            f"{format_number(float(dsr['test_statistic']), 4)} |"
        ),
        (
            "| Probabilité | "
            f"{format_percent(float(psr['probability']), 4)} | "
            f"{format_percent(float(dsr['probability']), 4)} |"
        ),
        (
            "| Statut méthodologique | "
            f"`{psr['methodological_status']}` | "
            f"`{dsr['methodological_status']}` |"
        ),
        "",
        (
            "Le PSR corrige la non-normalité empirique mais ne "
            "corrige pas explicitement la dépendance sérielle. "
            "Le DSR repose sur quinze essais agrégés ; la matrice "
            "sous-jacente n'est pas publiée."
        ),
        "",
        "## Tableau 6.2 - White Reality Check et Hansen SPA",
        "",
        ("| Test | P-value publiée | Qualification |"),
        "|---|---:|---|",
        (
            "| White Reality Check | "
            f"{format_probability(float(multiple['white_reality_check']['reported_p_value']))} "
            f"| `{multiple['white_reality_check']['methodological_status']}` |"
        ),
        (
            "| Hansen SPA | "
            f"{format_probability(float(multiple['hansen_spa']['reported_p_value']))} "
            f"| `{multiple['hansen_spa']['methodological_status']}` |"
        ),
        "",
        (f"- Référence nulle : `{multiple['benchmark']}`"),
        (f"- Candidats : {multiple['candidate_count']}"),
        (f"- Répétitions : {multiple['repetitions']}"),
        (f"- Taille de bloc : {multiple['block_size']}"),
        "",
        (
            "\\* Les valeurs nulles publiées sont bornées par la "
            "résolution de la procédure de rééchantillonnage finie "
            "et ne constituent pas des zéros mathématiques."
        ),
        "",
        "## Tableau 6.3 - CSCV et Probability of Backtest Overfitting",
        "",
        "| Mesure | Valeur |",
        "|---|---:|",
        (f"| Blocs CSCV | {pbo['blocks']} |"),
        (f"| Candidats | {pbo['candidate_count']} |"),
        (f"| Combinaisons par configuration | {pbo['combinations_per_setting']} |"),
        (f"| Configurations testées | {pbo['tested_setting_count']} |"),
        (f"| PBO minimum | {format_percent(float(pbo['pbo_minimum']), 2)} |"),
        (f"| PBO médian | {format_percent(float(pbo['pbo_median']), 2)} |"),
        (f"| PBO moyen | {format_percent(float(pbo['pbo_mean']), 2)} |"),
        (f"| PBO maximum | {format_percent(float(pbo['pbo_maximum']), 2)} |"),
        (
            "| Résultats sous 20 % | "
            f"{pbo['results_below_0_20']} sur "
            f"{pbo['tested_setting_count']} |"
        ),
        "",
        (
            "Les configurations exactes et la matrice des candidats "
            "demeurent non publiées. Les agrégats réduisent le risque "
            "apparent de surapprentissage sans démontrer son absence."
        ),
        "",
        "## Tableau 6.4 - Moving-block bootstrap face aux références",
        "",
        (
            "| Référence | Écart de CAGR | Surperformance log. "
            "| IC 95 % | P-value | Verdict officiel |"
        ),
        "|---|---:|---:|---:|---:|---|",
    ]

    benchmark_records = sorted(
        bootstrap["records"],
        key=lambda record: float(record["cagr_difference"]),
        reverse=True,
    )

    for record in benchmark_records:
        lower = float(record["ci95_lower_annualized_log"])
        upper = float(record["ci95_upper_annualized_log"])

        verdict = (
            "Significatif"
            if bool(record["significant_compounded_outperformance"])
            else "Non significatif"
        )

        lines.append(
            "| "
            f"{benchmark_label(str(record['benchmark']))} | "
            f"{format_percent(float(record['cagr_difference']), 2)} | "
            f"{format_percent(float(record['annualized_log_outperformance']), 2)} | "
            f"[{format_percent(lower, 2)} ; {format_percent(upper, 2)}] | "
            f"{format_percent(float(record['one_sided_p_value']), 2)} | "
            f"{verdict} |"
        )

    lines.extend(
        [
            "",
            (
                "Règle contrôlée : le verdict est positif uniquement "
                "si la p-value unilatérale est inférieure à 5 % et si "
                "la borne basse de l'intervalle à 95 % est strictement "
                "positive."
            ),
            "",
            (
                "Les onze écarts de CAGR sont positifs. Deux "
                "comparaisons sur onze satisfont la règle complète : "
                "allocation fixe à 50 % et HMM à trois états."
            ),
            "",
            "## Tableau 6.5A - Sensibilité Newey-West du Sharpe",
            "",
            ("| Retards | Sharpe HAC | Inflation de volatilité |"),
            "|---:|---:|---:|",
        ]
    )

    for record in temporal["hac_sensitivity_records"]:
        lines.append(
            "| "
            f"{record['lag_count']} | "
            f"{format_number(float(record['hac_adjusted_annualized_sharpe']), 4)} | "
            f"{format_number(float(record['volatility_inflation_factor']), 4)} |"
        )

    lines.extend(
        [
            "",
            (
                "Le choix canonique de vingt et un retards réduit le "
                "Sharpe annualisé de "
                f"{format_number(float(temporal['conventional_annualized_sharpe']), 4)} "
                "à "
                f"{format_number(float(temporal['canonical_hac_adjusted_annualized_sharpe']), 4)}."
            ),
            "",
            (
                "Aucun calcul HAC équivalent du bitcoin passif n'est "
                "présent dans l'artefact applicable."
            ),
            "",
            "## Tableau 6.5B - Bootstrap circulaire du Sharpe",
            "",
            ("| Taille de bloc | Médiane | Borne basse 95 % | Borne haute 95 % | Part positive |"),
            "|---:|---:|---:|---:|---:|",
        ]
    )

    for record in temporal["bootstrap_sensitivity_records"]:
        lines.append(
            "| "
            f"{record['block_size']} | "
            f"{format_number(float(record['bootstrap_median']), 4)} | "
            f"{format_number(float(record['interval_lower']), 4)} | "
            f"{format_number(float(record['interval_upper']), 4)} | "
            f"{format_percent(float(record['bootstrap_positive_share']), 1)} |"
        )

    lines.extend(
        [
            "",
            "## Tableau 6.5C - Diagnostics de Ljung-Box",
            "",
            "| Série | Retards | Statistique | P-value |",
            "|---|---:|---:|---:|",
        ]
    )

    for record in temporal["ljung_box_records"]:
        series = (
            "Rendements"
            if record["series"] == "periodic_returns"
            else "Rendements centrés au carré"
        )

        lines.append(
            "| "
            f"{series} | "
            f"{record['lag_count']} | "
            f"{format_number(float(record['statistic']), 4)} | "
            f"{format_scientific(float(record['p_value']))} |"
        )

    lines.extend(
        [
            "",
            "## Tableau 6.6 - Lecture consolidée",
            "",
            "| Dimension | Résultat contrôlé | Lecture autorisée |",
            "|---|---|---|",
            (
                "| Sharpe probabiliste | "
                f"{format_percent(float(psr['probability']), 4)} "
                "| Probabilité très élevée sous les hypothèses du test ; "
                "dépendance sérielle non explicitement corrigée |"
            ),
            (
                "| Sharpe déflaté | "
                f"{format_percent(float(dsr['probability']), 4)} "
                "| Résultat favorable après prise en compte de quinze "
                "essais agrégés ; matrice privée |"
            ),
            (
                "| Tests multiples | P-values publiées à zéro "
                "| Résultat favorable, borné par la résolution des "
                "2 000 répétitions |"
            ),
            (
                "| PBO | "
                f"Médiane {format_percent(float(pbo['pbo_median']), 2)} "
                "| Risque de surapprentissage réduit mais non annulé |"
            ),
            (
                "| Bootstrap contre les références | "
                f"{bootstrap['positive_cagr_differences']} écarts positifs, "
                f"{bootstrap['significant_at_5_percent']} significatifs "
                "| La surperformance historique n'est pas universellement "
                "significative |"
            ),
            (
                "| Dépendance temporelle | "
                f"Sharpe HAC 21 = "
                f"{format_number(float(temporal['canonical_hac_adjusted_annualized_sharpe']), 4)} "
                "| Le résultat reste positif après correction linéaire "
                "de la dépendance temporelle |"
            ),
            (
                "| Bootstrap circulaire | Toutes les bornes basses positives "
                "| Robustesse favorable sur les tailles de bloc publiées, "
                "conditionnelle au jeu de sensibilité |"
            ),
            "",
            "## Limites obligatoires",
            "",
            (
                "- L'analyse est historique et rétrospective ; elle ne "
                "constitue pas une validation indépendante."
            ),
            (
                "- Les matrices de candidats, observations rééchantillonnées "
                "et configurations exactes restent non publiées."
            ),
            (
                "- Newey-West traite la dépendance sérielle linéaire sans "
                "modéliser l'intégralité de la distribution conditionnelle."
            ),
            (
                "- Les conclusions bootstrap demeurent conditionnelles aux "
                "tailles de bloc et répétitions publiées."
            ),
            (
                "- Aucun résultat ne démontre l'absence de surapprentissage "
                "ni ne garantit une performance future."
            ),
            "",
        ]
    )

    markdown = "\n".join(lines)

    corrections = {
        "Verdict officiel|": "Verdict officiel |",
        "Significatif|": "Significatif |",
        "essaisagrégés": "essais agrégés",
        "répétitionspubliées": "répétitions publiées",
    }

    for incorrect, correct in corrections.items():
        markdown = markdown.replace(
            incorrect,
            correct,
        )

    MARKDOWN_PATH.write_text(
        markdown,
        encoding="utf-8",
    )


def update_manifest() -> None:
    controlled_paths = [
        SUMMARY_PATH,
        MARKDOWN_PATH,
        FIGURE_PBO,
        FIGURE_PVALUES,
        FIGURE_INTERVALS,
        FIGURE_HAC,
        FIGURE_BOOTSTRAP,
        Path(__file__).resolve(),
    ]

    records = []

    for path in sorted(
        controlled_paths,
        key=lambda item: item.relative_to(ROOT).as_posix(),
    ):
        require(
            path.is_file(),
            f"Fichier contrôlé absent : {path.relative_to(ROOT)}",
        )

        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest = {
        "schema_version": 1,
        "package": "part_vi_statistical_report_support",
        "model": "Nostra AI V5.246",
        "source_release": "v0.3.0",
        "period": {
            "start": "2020-05-14",
            "end": "2026-06-02",
            "observations": OBSERVATIONS,
        },
        "status": (
            "Tableaux, figures et agrégats institutionnels "
            "de validité statistique dérivés exclusivement "
            "des six exports publics gelés de la release v0.3.0."
        ),
        "files": records,
    }

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
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

    payloads = load_sources()

    validate_sources(payloads)

    summary = build_summary(payloads)

    write_summary(summary)
    write_markdown(payloads)

    generate_pbo_figure(payloads["backtest_overfitting"]["data"])
    generate_pvalue_figure(payloads["moving_block_bootstrap"]["data"])
    generate_interval_figure(payloads["moving_block_bootstrap"]["data"])
    generate_hac_figure(payloads["temporal_dependence_sharpe"]["data"])
    generate_circular_bootstrap_figure(payloads["temporal_dependence_sharpe"]["data"])

    update_manifest()

    from generate_part_vi_bitcoin_hac import (
        main as generate_bitcoin_hac,
    )
    from integrate_part_vi_bitcoin_hac import (
        integrate as integrate_bitcoin_hac,
    )

    generate_bitcoin_hac()
    integrate_bitcoin_hac()

    print("PASS_PART_VI_STATISTICAL_ANALYSIS")

    for path in [
        SUMMARY_PATH,
        MARKDOWN_PATH,
        FIGURE_PBO,
        FIGURE_PVALUES,
        FIGURE_INTERVALS,
        FIGURE_HAC,
        FIGURE_BOOTSTRAP,
        MANIFEST_PATH,
        CHECKSUMS_PATH,
    ]:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
