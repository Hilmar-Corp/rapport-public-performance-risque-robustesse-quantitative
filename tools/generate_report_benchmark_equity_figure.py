#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

EXPECTED_OBSERVATIONS = 2211
EXPECTED_NOSTRA_FINAL = 12.863641976380386
EXPECTED_PUBLIC_CURVES = 11


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def detect_date_column(frame: pd.DataFrame) -> str:
    candidates = (
        "timestamp",
        "date",
        "datetime",
        "time",
        "observation_date",
    )

    lower_to_original = {column.lower(): column for column in frame.columns}

    for candidate in candidates:
        if candidate in lower_to_original:
            return lower_to_original[candidate]

    raise ValueError(
        f"Aucune colonne de date reconnue. Colonnes disponibles : {list(frame.columns)}"
    )


def normalize_name(column: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", column.lower()).strip("_")


def public_label(column: str) -> str:
    name = normalize_name(column)

    mappings = (
        (("buy_and_hold", "buyhold"), "Bitcoin passif"),
        (("fixed_50", "constant_50"), "Allocation constante 50 %"),
        (("momentum_30", "mom_30"), "Momentum 30 j"),
        (("momentum_60", "mom_60"), "Momentum 60 j"),
        (("momentum_90", "mom_90"), "Momentum 90 j"),
        (("momentum_180", "mom_180"), "Momentum 180 j"),
        (("momentum_270", "mom_270"), "Momentum 270 j"),
        (("ma_50_200", "moving_average_50_200"), "Moyennes mobiles 50/200"),
        (("vol_target_14", "volatility_target_14"), "Ciblage de volatilité 14 j"),
        (("vol_target_30", "volatility_target_30"), "Ciblage de volatilité 30 j"),
        (
            ("hmm_3_state", "hmm_gaussian", "hmm_walkforward"),
            "HMM gaussien 3 états",
        ),
    )

    for aliases, label in mappings:
        if any(alias in name for alias in aliases):
            return label

    cleaned = re.sub(r"_?equity.*$", "", name)
    return cleaned.replace("_", " ").title()


def load_public_curves(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    date_column = detect_date_column(frame)

    frame[date_column] = pd.to_datetime(frame[date_column], utc=True, errors="raise")
    frame = frame.sort_values(date_column).drop_duplicates(date_column)

    equity_columns = [
        column for column in frame.columns if column != date_column and "equity" in column.lower()
    ]

    if len(equity_columns) != EXPECTED_PUBLIC_CURVES:
        raise ValueError(
            f"{EXPECTED_PUBLIC_CURVES} courbes publiques attendues, "
            f"{len(equity_columns)} détectées : {equity_columns}"
        )

    result = frame[[date_column, *equity_columns]].copy()
    result = result.rename(columns={date_column: "timestamp"})

    for column in equity_columns:
        result[column] = pd.to_numeric(result[column], errors="raise")

    return result


def load_nostra_curve(
    path: Path,
    date_column: str,
    equity_column: str,
) -> pd.DataFrame:
    frame = pd.read_csv(path)

    missing = [column for column in (date_column, equity_column) if column not in frame.columns]

    if missing:
        raise ValueError(
            f"Colonnes Nostra absentes : {missing}. Colonnes disponibles : {list(frame.columns)}"
        )

    result = frame[[date_column, equity_column]].copy()
    result[date_column] = pd.to_datetime(
        result[date_column],
        utc=True,
        errors="raise",
    )
    result[equity_column] = pd.to_numeric(
        result[equity_column],
        errors="raise",
    )

    result = (
        result.sort_values(date_column)
        .drop_duplicates(date_column)
        .rename(
            columns={
                date_column: "timestamp",
                equity_column: "nostra_equity",
            }
        )
    )

    return result


def validate(frame: pd.DataFrame, public_columns: list[str]) -> None:
    if len(frame) != EXPECTED_OBSERVATIONS:
        raise ValueError(
            f"{EXPECTED_OBSERVATIONS} observations attendues, "
            f"{len(frame)} obtenues après réconciliation."
        )

    if frame.isna().any().any():
        missing = frame.isna().sum()
        raise ValueError(f"Valeurs manquantes après réconciliation :\n{missing[missing > 0]}")

    nostra_final = float(frame["nostra_equity"].iloc[-1])

    if abs(nostra_final - EXPECTED_NOSTRA_FINAL) > 1e-10:
        raise ValueError(
            "Capital final Nostra non réconcilié : "
            f"{nostra_final:.15f}, attendu {EXPECTED_NOSTRA_FINAL:.15f}."
        )

    for column in ["nostra_equity", *public_columns]:
        if (frame[column] <= 0).any():
            raise ValueError(f"La courbe {column} contient une valeur nulle ou négative.")


def plot_equity_curves(
    frame: pd.DataFrame,
    public_columns: list[str],
    output: Path,
) -> None:
    benchmark_order = [
        "Bitcoin passif",
        "Allocation constante 50 %",
        "Momentum 30 j",
        "Momentum 60 j",
        "Momentum 90 j",
        "Momentum 180 j",
        "Momentum 270 j",
        "Moyennes mobiles 50/200",
        "Ciblage de volatilité 14 j",
        "Ciblage de volatilité 30 j",
        "HMM gaussien 3 états",
    ]

    columns_by_label = {public_label(column): column for column in public_columns}

    missing = [label for label in benchmark_order if label not in columns_by_label]

    if missing:
        raise ValueError("Courbes publiques absentes : " + ", ".join(missing))

    nostra_color = "#132B3F"
    benchmark_color = "#6F9CAF"
    grid_color = "#E4E8EB"
    axis_color = "#A8B0B7"
    text_color = "#26313A"

    figure, axes = plt.subplots(
        nrows=4,
        ncols=3,
        figsize=(10.6, 11.4),
        sharex=True,
        sharey=True,
        facecolor="white",
    )

    axes_flat = axes.ravel()

    maximum = float(frame[["nostra_equity", *public_columns]].max().max())

    y_limit = max(16.0, maximum * 1.035)
    nostra_final = float(frame["nostra_equity"].iloc[-1])

    def format_multiple(value: float) -> str:
        return f"{value:.2f}".replace(".", ",") + "\u00d7"

    for index, benchmark_label in enumerate(benchmark_order):
        axis = axes_flat[index]
        benchmark_column = columns_by_label[benchmark_label]
        benchmark_final = float(frame[benchmark_column].iloc[-1])

        axis.set_facecolor("white")

        axis.plot(
            frame["timestamp"],
            frame["nostra_equity"],
            linewidth=1.45,
            color=nostra_color,
            zorder=3,
        )

        axis.plot(
            frame["timestamp"],
            frame[benchmark_column],
            linewidth=1.05,
            color=benchmark_color,
            zorder=2,
        )

        axis.scatter(
            frame["timestamp"].iloc[-1],
            nostra_final,
            s=14,
            color=nostra_color,
            zorder=4,
        )

        axis.scatter(
            frame["timestamp"].iloc[-1],
            benchmark_final,
            s=14,
            color=benchmark_color,
            zorder=4,
        )

        axis.set_title(
            benchmark_label,
            loc="left",
            fontsize=9.2,
            fontweight="bold",
            color=text_color,
            pad=8,
        )

        axis.text(
            0.985,
            0.955,
            format_multiple(benchmark_final),
            transform=axis.transAxes,
            ha="right",
            va="top",
            fontsize=7.6,
            color=benchmark_color,
            fontweight="bold",
        )

        axis.set_ylim(0, y_limit)
        axis.set_yticks([0, 4, 8, 12, 16])

        axis.grid(
            axis="y",
            linewidth=0.55,
            color=grid_color,
        )

        axis.grid(axis="x", visible=False)
        axis.set_axisbelow(True)
        axis.margins(x=0)

        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

        axis.spines["left"].set_color(axis_color)
        axis.spines["bottom"].set_color(axis_color)

        axis.spines["left"].set_linewidth(0.6)
        axis.spines["bottom"].set_linewidth(0.6)

        axis.tick_params(
            axis="both",
            labelsize=7.3,
            width=0.55,
            colors="#59636C",
        )

        axis.xaxis.set_major_locator(mdates.YearLocator(2))

        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    axes_flat[-1].axis("off")

    for row in range(4):
        axes[row, 0].set_ylabel(
            "Capital, base 1",
            fontsize=7.8,
            color=text_color,
        )

    for column in range(3):
        if axes[3, column] is not axes_flat[-1]:
            axes[3, column].set_xlabel(
                "Date",
                fontsize=7.8,
                color=text_color,
            )

    legend_handles = [
        plt.Line2D(
            [0],
            [0],
            color=nostra_color,
            linewidth=1.7,
            label=("Nostra AI V5.246  ·  " + format_multiple(nostra_final)),
        ),
        plt.Line2D(
            [0],
            [0],
            color=benchmark_color,
            linewidth=1.25,
            label="Stratégie publique de référence",
        ),
    ]

    figure.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.985),
        frameon=False,
        ncol=2,
        fontsize=8.8,
        handlelength=3.0,
        columnspacing=2.5,
    )

    figure.subplots_adjust(
        left=0.075,
        right=0.985,
        top=0.94,
        bottom=0.055,
        hspace=0.34,
        wspace=0.18,
    )

    output.parent.mkdir(parents=True, exist_ok=True)

    figure.savefig(
        output,
        dpi=320,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(figure)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Génère la figure quotidienne comparant Nostra AI "
            "aux onze stratégies publiques de référence."
        )
    )

    parser.add_argument(
        "--public-curves",
        type=Path,
        default=Path("artifacts/releases/v0.2.1/baseline_daily_curves.csv"),
    )
    parser.add_argument(
        "--nostra-input",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--nostra-date-column",
        default="timestamp",
    )
    parser.add_argument(
        "--nostra-equity-column",
        default="v5246_equity_25bps",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/figures/figure_5_3_nostra_vs_11_references.png"),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    public = load_public_curves(arguments.public_curves)
    nostra = load_nostra_curve(
        arguments.nostra_input,
        arguments.nostra_date_column,
        arguments.nostra_equity_column,
    )

    public_columns = [column for column in public.columns if column != "timestamp"]

    combined = public.merge(
        nostra,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )

    validate(combined, public_columns)
    plot_equity_curves(combined, public_columns, arguments.output)

    print()
    print("=== FIGURE GÉNÉRÉE ===")
    print(arguments.output.resolve())

    print()
    print("=== PÉRIMÈTRE ===")
    print(f"Observations quotidiennes : {len(combined)}")
    print(f"Stratégies publiques : {len(public_columns)}")
    print("Série Nostra AI : 1")

    print()
    print("=== VALEURS FINALES ===")
    print(f"Nostra AI V5.246 : {combined['nostra_equity'].iloc[-1]:.12f}")

    for column in sorted(
        public_columns,
        key=lambda item: combined[item].iloc[-1],
        reverse=True,
    ):
        print(f"{public_label(column)} : {combined[column].iloc[-1]:.12f}")

    print()
    print("=== TRAÇABILITÉ ===")
    print(f"Source publique : {arguments.public_curves.resolve()}")
    print(f"SHA-256 public : {sha256_file(arguments.public_curves)}")
    print(f"Source privée : {arguments.nostra_input.resolve()}")
    print(f"SHA-256 privé : {sha256_file(arguments.nostra_input)}")


if __name__ == "__main__":
    main()
