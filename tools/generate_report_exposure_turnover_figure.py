#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

EXPECTED_OBSERVATIONS = 2211
EXPECTED_START = pd.Timestamp("2020-05-14", tz="UTC")
EXPECTED_END = pd.Timestamp("2026-06-02", tz="UTC")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def load_data(
    path: Path,
    date_column: str,
    position_column: str,
) -> pd.DataFrame:
    frame = pd.read_csv(path)

    missing = [column for column in (date_column, position_column) if column not in frame.columns]

    if missing:
        raise ValueError(
            f"Colonnes absentes : {missing}\nColonnes disponibles : {list(frame.columns)}"
        )

    frame = frame[[date_column, position_column]].copy()

    frame[date_column] = pd.to_datetime(
        frame[date_column],
        utc=True,
        errors="raise",
    )

    frame[position_column] = pd.to_numeric(
        frame[position_column],
        errors="raise",
    )

    frame = (
        frame.sort_values(date_column)
        .drop_duplicates(date_column)
        .rename(
            columns={
                date_column: "timestamp",
                position_column: "exposure",
            }
        )
        .reset_index(drop=True)
    )

    if len(frame) != EXPECTED_OBSERVATIONS:
        raise ValueError(f"{EXPECTED_OBSERVATIONS} observations attendues, {len(frame)} obtenues.")

    if frame["timestamp"].iloc[0] != EXPECTED_START:
        raise ValueError(f"Date initiale incorrecte : {frame['timestamp'].iloc[0]}")

    if frame["timestamp"].iloc[-1] != EXPECTED_END:
        raise ValueError(f"Date finale incorrecte : {frame['timestamp'].iloc[-1]}")

    if frame["exposure"].isna().any():
        raise ValueError("La série d'exposition contient des valeurs manquantes.")

    frame["absolute_exposure"] = frame["exposure"].abs()

    previous_exposure = frame["exposure"].shift(
        1,
        fill_value=0.0,
    )

    frame["turnover"] = (frame["exposure"] - previous_exposure).abs()

    frame["month"] = frame["timestamp"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()

    return frame


def aggregate_monthly(frame: pd.DataFrame) -> pd.DataFrame:
    monthly = frame.groupby("month", as_index=False).agg(
        exposure_mean=("exposure", "mean"),
        absolute_exposure_mean=("absolute_exposure", "mean"),
        turnover_sum=("turnover", "sum"),
    )

    return monthly


def generate_figure(
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
    output: Path,
) -> None:
    exposure_mean = float(daily["exposure"].mean())
    absolute_mean = float(daily["absolute_exposure"].mean())

    figure, axes = plt.subplots(
        nrows=3,
        ncols=1,
        figsize=(10.4, 8.6),
        sharex=True,
        gridspec_kw={
            "height_ratios": [1.0, 1.0, 0.9],
        },
    )

    exposure_color = "#173B57"
    absolute_color = "#3E7480"
    turnover_color = "#6F7C86"
    reference_color = "#9BA5AC"
    grid_color = "#E1E5E8"

    # A. Exposition signée
    axis = axes[0]

    axis.plot(
        monthly["month"],
        monthly["exposure_mean"] * 100,
        linewidth=1.45,
        color=exposure_color,
    )

    axis.axhline(
        0,
        linewidth=0.8,
        color="#515A61",
    )

    axis.axhline(
        exposure_mean * 100,
        linewidth=0.9,
        linestyle="--",
        color=reference_color,
        label=(f"Moyenne de période : {exposure_mean * 100:.2f} %"),
    )

    axis.set_ylim(-12, 102)
    axis.set_ylabel("Exposition")
    axis.set_title(
        "A. Exposition moyenne mensuelle",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )

    axis.yaxis.set_major_formatter(PercentFormatter(xmax=100))

    axis.legend(
        loc="upper left",
        frameon=False,
        fontsize=8.5,
    )

    # B. Exposition absolue
    axis = axes[1]

    axis.plot(
        monthly["month"],
        monthly["absolute_exposure_mean"] * 100,
        linewidth=1.45,
        color=absolute_color,
    )

    axis.axhline(
        absolute_mean * 100,
        linewidth=0.9,
        linestyle="--",
        color=reference_color,
        label=(f"Moyenne de période : {absolute_mean * 100:.2f} %"),
    )

    axis.set_ylim(0, 102)
    axis.set_ylabel("Exposition absolue")
    axis.set_title(
        "B. Exposition absolue moyenne mensuelle",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )

    axis.yaxis.set_major_formatter(PercentFormatter(xmax=100))

    axis.legend(
        loc="upper left",
        frameon=False,
        fontsize=8.5,
    )

    # C. Rotation
    axis = axes[2]

    axis.bar(
        monthly["month"],
        monthly["turnover_sum"],
        width=20,
        color=turnover_color,
        alpha=0.88,
    )

    axis.set_ylim(bottom=0)
    axis.set_ylabel("Unités d'exposition")
    axis.set_title(
        "C. Rotation mensuelle",
        loc="left",
        fontsize=11,
        fontweight="bold",
    )

    axis.set_xlabel("Date")

    # Présentation commune
    for axis in axes:
        axis.grid(
            axis="y",
            linewidth=0.6,
            color=grid_color,
        )

        axis.grid(axis="x", visible=False)
        axis.set_axisbelow(True)

        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

        axis.spines["left"].set_color("#A5ADB3")
        axis.spines["bottom"].set_color("#A5ADB3")

        axis.tick_params(
            axis="both",
            labelsize=8.5,
            colors="#485159",
        )

    axes[-1].xaxis.set_major_locator(mdates.YearLocator())

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    figure.text(
        0.075,
        0.015,
        "Agrégats mensuels calculés à partir des expositions "
        "quotidiennes appliquées. La rotation inclut le mouvement "
        "initial depuis une exposition nulle.",
        fontsize=7.7,
        color="#626C74",
    )

    figure.subplots_adjust(
        left=0.10,
        right=0.985,
        top=0.975,
        bottom=0.085,
        hspace=0.34,
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
            "Génère la figure publique agrégée présentant "
            "l'exposition, l'exposition absolue et la rotation."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Fichier privé contenant les expositions quotidiennes.",
    )

    parser.add_argument(
        "--date-column",
        default="timestamp",
    )

    parser.add_argument(
        "--position-column",
        default="v5246_position",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/figures/figure_5_4_exposition_absolue_rotation.png"),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    input_path = arguments.input.expanduser().resolve()
    output_path = arguments.output.expanduser().resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Fichier privé introuvable : {input_path}")

    daily = load_data(
        input_path,
        arguments.date_column,
        arguments.position_column,
    )

    monthly = aggregate_monthly(daily)

    generate_figure(
        daily,
        monthly,
        output_path,
    )

    print()
    print("=== FIGURE GÉNÉRÉE ===")
    print(output_path)

    print()
    print("=== MÉTRIQUES CALCULÉES ===")
    print(f"Exposition moyenne : {daily['exposure'].mean() * 100:.8f} %")
    print(f"Exposition absolue moyenne : {daily['absolute_exposure'].mean() * 100:.8f} %")
    print(f"Exposition minimale : {daily['exposure'].min() * 100:.8f} %")
    print(f"Exposition maximale : {daily['exposure'].max() * 100:.8f} %")
    print(f"Rotation cumulée : {daily['turnover'].sum():.12f}")

    print()
    print("=== PÉRIMÈTRE ===")
    print(f"Observations quotidiennes : {len(daily)}")
    print(f"Mois représentés : {len(monthly)}")
    print(f"Période : {daily['timestamp'].iloc[0]} au {daily['timestamp'].iloc[-1]}")

    print()
    print("=== TRAÇABILITÉ ===")
    print(f"Source privée : {input_path}")
    print(f"SHA-256 : {sha256_file(input_path)}")


if __name__ == "__main__":
    main()
