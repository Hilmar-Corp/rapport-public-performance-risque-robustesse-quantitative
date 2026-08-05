#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_vi"

SUMMARY_PATH = SUPPORT_DIR / "part_vi_statistical_summary.json"

BITCOIN_HAC_PATH = SUPPORT_DIR / "bitcoin_passive_hac_sharpe.json"

MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = ROOT / "docs" / "tables" / "part_vi_statistical_results.md"

FIGURE_HAC_PATH = ROOT / "docs" / "figures" / "figure_6_4_hac_sharpe_sensitivity.png"

MAIN_GENERATOR_PATH = ROOT / "tools" / "generate_part_vi_statistical_analysis.py"

BITCOIN_GENERATOR_PATH = ROOT / "tools" / "generate_part_vi_bitcoin_hac.py"

INTEGRATOR_PATH = Path(__file__).resolve()

HAC_LAGS = [5, 7, 10, 21, 30, 60]

NOSTRA_COLOR = "#1f77b4"
BITCOIN_COLOR = "#ff7f0e"
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.is_file(),
        f"Fichier absent : {path.relative_to(ROOT)}",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    require(
        isinstance(payload, dict),
        f"Objet JSON invalide : {path.relative_to(ROOT)}",
    )

    return payload


def format_number(
    value: float,
    decimals: int = 4,
) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def validate(
    summary: dict[str, Any],
    bitcoin: dict[str, Any],
) -> None:
    temporal = summary["temporal_dependence_sharpe"]

    require(
        summary["period"]["observations"] == 2211,
        "Période Partie VI non conforme.",
    )

    require(
        bitcoin["period"]["observations"] == 2211,
        "Période bitcoin non conforme.",
    )

    require(
        bitcoin["period"]["annualization"] == 365,
        "Annualisation bitcoin non conforme.",
    )

    require(
        [int(record["lag_count"]) for record in temporal["hac_sensitivity_records"]] == HAC_LAGS,
        "Retards HAC Nostra non conformes.",
    )

    require(
        [int(record["lag_count"]) for record in bitcoin["sensitivity_records"]] == HAC_LAGS,
        "Retards HAC bitcoin non conformes.",
    )

    nostra_hac = float(temporal["canonical_hac_adjusted_annualized_sharpe"])

    bitcoin_hac = float(bitcoin["canonical"]["hac_adjusted_annualized_sharpe"])

    require(
        abs(nostra_hac - 1.4931827873589063) < 1e-14,
        "Sharpe HAC Nostra non conforme.",
    )

    require(
        abs(bitcoin_hac - 0.8183668937097701) < 1e-14,
        "Sharpe HAC bitcoin non conforme.",
    )


def update_summary(
    summary: dict[str, Any],
    bitcoin: dict[str, Any],
) -> None:
    temporal = summary["temporal_dependence_sharpe"]

    reading = summary["consolidated_reading"]

    nostra_hac = float(temporal["canonical_hac_adjusted_annualized_sharpe"])

    bitcoin_hac = float(bitcoin["canonical"]["hac_adjusted_annualized_sharpe"])

    summary["bitcoin_passive_hac_sharpe"] = bitcoin

    summary["supplementary_public_source"] = {
        "purpose": ("Calculation of the bitcoin passive Newey-West-adjusted Sharpe ratio"),
        **bitcoin["source"],
    }

    reading["bitcoin_conventional_annualized_sharpe"] = float(
        bitcoin["canonical"]["conventional_annualized_sharpe"]
    )

    reading["bitcoin_canonical_hac_adjusted_sharpe"] = bitcoin_hac

    reading["bitcoin_canonical_volatility_inflation_factor"] = float(
        bitcoin["canonical"]["volatility_inflation_factor"]
    )

    reading["canonical_hac_sharpe_advantage"] = nostra_hac - bitcoin_hac

    summary["status"] = (
        "Transformation contrôlée des six agrégats "
        "statistiques publics gelés de la release "
        "v0.3.0, complétée par le calcul Newey-West "
        "du bitcoin passif à partir de sa courbe "
        "quotidienne publique gelée."
    )

    SUMMARY_PATH.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_hac_markdown(
    summary: dict[str, Any],
    bitcoin: dict[str, Any],
) -> str:
    temporal = summary["temporal_dependence_sharpe"]

    nostra_records = {
        int(record["lag_count"]): record for record in temporal["hac_sensitivity_records"]
    }

    bitcoin_records = {
        int(record["lag_count"]): record for record in bitcoin["sensitivity_records"]
    }

    lines = [
        "## Tableau 6.5A - Sensibilité Newey-West du Sharpe",
        "",
        ("| Retards | Nostra HAC | Bitcoin passif HAC | Inflation Nostra | Inflation bitcoin |"),
        "|---:|---:|---:|---:|---:|",
    ]

    for lag in HAC_LAGS:
        nostra = nostra_records[lag]
        btc = bitcoin_records[lag]

        lines.append(
            "| "
            f"{lag} | "
            f"{format_number(float(nostra['hac_adjusted_annualized_sharpe']))} | "
            f"{format_number(float(btc['hac_adjusted_annualized_sharpe']))} | "
            f"{format_number(float(nostra['volatility_inflation_factor']))} | "
            f"{format_number(float(btc['volatility_inflation_factor']))} |"
        )

    nostra_conventional = float(temporal["conventional_annualized_sharpe"])

    bitcoin_conventional = float(bitcoin["canonical"]["conventional_annualized_sharpe"])

    nostra_hac = float(temporal["canonical_hac_adjusted_annualized_sharpe"])

    bitcoin_hac = float(bitcoin["canonical"]["hac_adjusted_annualized_sharpe"])

    advantage = nostra_hac - bitcoin_hac

    lines.extend(
        [
            "",
            (
                "À vingt et un retards, le Sharpe "
                "annualisé de Nostra AI passe de "
                f"{format_number(nostra_conventional)} "
                "à "
                f"{format_number(nostra_hac)}, "
                "tandis que celui du bitcoin passif "
                "passe de "
                f"{format_number(bitcoin_conventional)} "
                "à "
                f"{format_number(bitcoin_hac)}."
            ),
            "",
            (
                "L'écart descriptif entre les deux "
                "Sharpes corrigés de Newey-West est "
                f"de +{format_number(advantage)} en "
                "faveur de Nostra AI. Cet écart ne "
                "constitue pas, à lui seul, un test "
                "statistique formel d'égalité entre "
                "les deux ratios."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def update_markdown(
    summary: dict[str, Any],
    bitcoin: dict[str, Any],
) -> None:
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")

    replacement = build_hac_markdown(
        summary,
        bitcoin,
    )

    pattern = re.compile(
        r"## Tableau 6\.5A.*?"
        r"(?=## Tableau 6\.5B)",
        flags=re.DOTALL,
    )

    markdown, count = pattern.subn(
        replacement,
        markdown,
        count=1,
    )

    require(
        count == 1,
        "Section Tableau 6.5A introuvable.",
    )

    consolidated_row = (
        "| Dépendance temporelle | "
        "Sharpe HAC 21 : Nostra 1,4932 ; "
        "bitcoin passif 0,8184 "
        "| Les deux ratios restent positifs après "
        "correction ; l'écart demeure descriptif |"
    )

    markdown, count = re.subn(
        r"\| Dépendance temporelle \|.*?\|\n",
        consolidated_row + "\n",
        markdown,
        count=1,
    )

    require(
        count == 1,
        "Ligne consolidée de dépendance temporelle introuvable.",
    )

    require(
        "Aucun calcul HAC équivalent du bitcoin passif" not in markdown,
        "Ancienne limitation HAC encore présente.",
    )

    MARKDOWN_PATH.write_text(
        markdown,
        encoding="utf-8",
    )


def generate_hac_figure(
    summary: dict[str, Any],
    bitcoin: dict[str, Any],
) -> None:
    import matplotlib.pyplot as plt

    temporal = summary["temporal_dependence_sharpe"]

    nostra_records = temporal["hac_sensitivity_records"]

    bitcoin_records = bitcoin["sensitivity_records"]

    positions = list(range(len(HAC_LAGS)))

    nostra_values = [float(record["hac_adjusted_annualized_sharpe"]) for record in nostra_records]

    bitcoin_values = [float(record["hac_adjusted_annualized_sharpe"]) for record in bitcoin_records]

    nostra_conventional = float(temporal["conventional_annualized_sharpe"])

    bitcoin_conventional = float(bitcoin["canonical"]["conventional_annualized_sharpe"])

    figure, axis = plt.subplots(
        figsize=(10.5, 5.8),
    )

    axis.plot(
        positions,
        nostra_values,
        marker="o",
        linewidth=2.0,
        markersize=5.5,
        color=NOSTRA_COLOR,
        label="Nostra AI, Sharpe HAC",
        zorder=3,
    )

    axis.plot(
        positions,
        bitcoin_values,
        marker="o",
        linewidth=2.0,
        markersize=5.5,
        color=BITCOIN_COLOR,
        label="Bitcoin passif, Sharpe HAC",
        zorder=3,
    )

    axis.axhline(
        nostra_conventional,
        linestyle="--",
        linewidth=1.1,
        color=NOSTRA_COLOR,
        alpha=0.7,
        label=(f"Nostra conventionnel {format_number(nostra_conventional, 2)}"),
        zorder=2,
    )

    axis.axhline(
        bitcoin_conventional,
        linestyle="--",
        linewidth=1.1,
        color=BITCOIN_COLOR,
        alpha=0.7,
        label=(f"Bitcoin conventionnel {format_number(bitcoin_conventional, 2)}"),
        zorder=2,
    )

    canonical_position = HAC_LAGS.index(21)

    axis.scatter(
        canonical_position,
        nostra_values[canonical_position],
        s=85,
        color=NOSTRA_COLOR,
        edgecolor="white",
        linewidth=1.0,
        zorder=4,
    )

    axis.scatter(
        canonical_position,
        bitcoin_values[canonical_position],
        s=85,
        color=BITCOIN_COLOR,
        edgecolor="white",
        linewidth=1.0,
        zorder=4,
    )

    axis.set_xticks(
        positions,
        [str(lag) for lag in HAC_LAGS],
    )

    axis.set_xlabel("Configurations de retards Newey-West testées")

    axis.set_ylabel("Ratio de Sharpe annualisé")

    all_values = [
        *nostra_values,
        *bitcoin_values,
        nostra_conventional,
        bitcoin_conventional,
    ]

    axis.set_ylim(
        min(all_values) - 0.06,
        max(all_values) + 0.06,
    )

    axis.grid(
        axis="y",
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

    axis.legend(
        frameon=False,
        loc="center right",
        fontsize=8.5,
    )

    figure.tight_layout()

    figure.savefig(
        FIGURE_HAC_PATH,
        dpi=320,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Software": ("HilmarCorp controlled Part VI report support")},
    )

    plt.close(figure)


def update_manifest() -> None:
    controlled_paths = [
        SUMMARY_PATH,
        BITCOIN_HAC_PATH,
        MARKDOWN_PATH,
        ROOT / "docs" / "figures" / "figure_6_1_pbo_aggregate_sensitivity.png",
        ROOT / "docs" / "figures" / "figure_6_2_benchmark_bootstrap_pvalues.png",
        ROOT / "docs" / "figures" / "figure_6_3_benchmark_bootstrap_intervals.png",
        FIGURE_HAC_PATH,
        ROOT / "docs" / "figures" / "figure_6_5_circular_bootstrap_intervals.png",
        MAIN_GENERATOR_PATH,
        BITCOIN_GENERATOR_PATH,
        INTEGRATOR_PATH,
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
                "path": (path.relative_to(ROOT).as_posix()),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest = {
        "schema_version": 1,
        "package": ("part_vi_statistical_report_support"),
        "model": "Nostra AI V5.246",
        "source_release": "v0.3.0",
        "period": {
            "start": "2020-05-14",
            "end": "2026-06-02",
            "observations": 2211,
        },
        "status": (
            "Paquet statistique institutionnel de la "
            "Partie VI, complété par le calcul HAC du "
            "bitcoin passif à partir de sa courbe "
            "quotidienne publique gelée."
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


def integrate() -> None:
    summary = load_json(SUMMARY_PATH)
    bitcoin = load_json(BITCOIN_HAC_PATH)

    validate(summary, bitcoin)
    update_summary(summary, bitcoin)

    summary = load_json(SUMMARY_PATH)

    update_markdown(summary, bitcoin)
    generate_hac_figure(summary, bitcoin)
    update_manifest()

    print("PASS_PART_VI_BITCOIN_HAC_INTEGRATION")
    print(BITCOIN_HAC_PATH.relative_to(ROOT))
    print(MARKDOWN_PATH.relative_to(ROOT))
    print(FIGURE_HAC_PATH.relative_to(ROOT))


if __name__ == "__main__":
    integrate()
