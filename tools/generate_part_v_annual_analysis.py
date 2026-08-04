#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd


EXPECTED_OBSERVATIONS = 2211
EXPECTED_START = pd.Timestamp("2020-05-14", tz="UTC")
EXPECTED_END = pd.Timestamp("2026-06-02", tz="UTC")

EXPECTED_NOSTRA_FINAL = 12.863641976380386
EXPECTED_BITCOIN_FINAL = 7.212950328296465
EXPECTED_TURNOVER = 46.79247585

ANNUALIZATION_FACTOR = 365.0


PUBLIC_LABELS = {
    "buy_and_hold_equity": "Bitcoin passif",
    "fixed_50_equity": "Allocation constante 50 %",
    "momentum_30_equity": "Momentum 30 j",
    "momentum_60_equity": "Momentum 60 j",
    "momentum_90_equity": "Momentum 90 j",
    "momentum_180_equity": "Momentum 180 j",
    "momentum_270_equity": "Momentum 270 j",
    "ma_50_200_equity": "Moyennes mobiles 50/200",
    "vol_target_14_equity": "Ciblage de volatilité 14 j",
    "vol_target_30_equity": "Ciblage de volatilité 30 j",
    "hmm_3_state_walkforward_equity": "HMM gaussien 3 états",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def returns_from_equity(equity: pd.Series) -> pd.Series:
    returns = equity.pct_change()

    # Le capital antérieur à la première observation est fixé à 1.
    returns.iloc[0] = float(equity.iloc[0]) - 1.0

    if not np.isfinite(returns).all():
        raise ValueError("La série de rendements contient une valeur invalide.")

    return returns.astype(float)


def calendar_max_drawdown(returns: pd.Series) -> float:
    local_equity = (1.0 + returns).cumprod()

    running_max = np.maximum.accumulate(
        np.concatenate(
            [
                np.array([1.0]),
                local_equity.to_numpy(dtype=float),
            ]
        )
    )[1:]

    drawdown = (
        local_equity.to_numpy(dtype=float) / running_max
    ) - 1.0

    return float(np.min(drawdown))


def annual_sharpe(returns: pd.Series) -> float:
    volatility = float(returns.std(ddof=1))

    if volatility <= 0:
        return float("nan")

    return (
        float(returns.mean())
        / volatility
        * math.sqrt(ANNUALIZATION_FACTOR)
    )


def validate_dates(frame: pd.DataFrame) -> None:
    if len(frame) != EXPECTED_OBSERVATIONS:
        raise ValueError(
            f"{EXPECTED_OBSERVATIONS} observations attendues, "
            f"{len(frame)} obtenues."
        )

    first_date = frame["timestamp"].iloc[0]
    last_date = frame["timestamp"].iloc[-1]

    if first_date != EXPECTED_START:
        raise ValueError(
            f"Date initiale incorrecte : {first_date}"
        )

    if last_date != EXPECTED_END:
        raise ValueError(
            f"Date finale incorrecte : {last_date}"
        )


def load_private(
    path: Path,
    date_column: str,
    equity_column: str,
    position_column: str,
) -> pd.DataFrame:
    frame = pd.read_csv(path)

    required = [
        date_column,
        equity_column,
        position_column,
    ]

    missing = [
        column
        for column in required
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            f"Colonnes privées absentes : {missing}\n"
            f"Colonnes disponibles : {list(frame.columns)}"
        )

    frame = frame[required].copy()

    frame[date_column] = pd.to_datetime(
        frame[date_column],
        utc=True,
        errors="raise",
    )

    frame[equity_column] = pd.to_numeric(
        frame[equity_column],
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
                equity_column: "nostra_equity",
                position_column: "nostra_exposure",
            }
        )
        .reset_index(drop=True)
    )

    validate_dates(frame)

    final_equity = float(frame["nostra_equity"].iloc[-1])

    if abs(final_equity - EXPECTED_NOSTRA_FINAL) > 1e-10:
        raise ValueError(
            "Capital final Nostra non réconcilié : "
            f"{final_equity:.15f}"
        )

    frame["nostra_return"] = returns_from_equity(
        frame["nostra_equity"]
    )

    previous = frame["nostra_exposure"].shift(
        1,
        fill_value=0.0,
    )

    frame["turnover"] = (
        frame["nostra_exposure"] - previous
    ).abs()

    turnover = float(frame["turnover"].sum())

    if abs(turnover - EXPECTED_TURNOVER) > 1e-6:
        raise ValueError(
            "Rotation cumulée non réconciliée : "
            f"{turnover:.12f}"
        )

    return frame


def load_public(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)

    if "timestamp" not in frame.columns:
        raise ValueError(
            "La colonne timestamp est absente du fichier public."
        )

    missing = [
        column
        for column in PUBLIC_LABELS
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            "Courbes publiques absentes : "
            + ", ".join(missing)
        )

    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"],
        utc=True,
        errors="raise",
    )

    frame = (
        frame.sort_values("timestamp")
        .drop_duplicates("timestamp")
        .reset_index(drop=True)
    )

    validate_dates(frame)

    for column in PUBLIC_LABELS:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="raise",
        )

    final_bitcoin = float(
        frame["buy_and_hold_equity"].iloc[-1]
    )

    if abs(final_bitcoin - EXPECTED_BITCOIN_FINAL) > 1e-10:
        raise ValueError(
            "Capital final du bitcoin passif non réconcilié : "
            f"{final_bitcoin:.15f}"
        )

    return frame


def annual_metrics_for_returns(
    timestamps: pd.Series,
    returns: pd.Series,
    equity: pd.Series,
) -> pd.DataFrame:
    working = pd.DataFrame(
        {
            "timestamp": timestamps,
            "return": returns,
            "equity": equity,
        }
    )

    working["year"] = working["timestamp"].dt.year

    records: list[dict[str, float | int]] = []

    for year, group in working.groupby("year", sort=True):
        group_returns = group["return"].astype(float)

        compounded_return = float(
            (1.0 + group_returns).prod() - 1.0
        )

        volatility = float(
            group_returns.std(ddof=1)
            * math.sqrt(ANNUALIZATION_FACTOR)
        )

        records.append(
            {
                "year": int(year),
                "observations": int(len(group)),
                "return": compounded_return,
                "annualized_volatility": volatility,
                "sharpe": annual_sharpe(group_returns),
                "maximum_drawdown": calendar_max_drawdown(
                    group_returns
                ),
                "ending_equity": float(group["equity"].iloc[-1]),
            }
        )

    return pd.DataFrame(records)


def build_core_annual_table(
    combined: pd.DataFrame,
    cost_bps: float,
) -> pd.DataFrame:
    nostra = annual_metrics_for_returns(
        combined["timestamp"],
        combined["nostra_return"],
        combined["nostra_equity"],
    ).add_prefix("nostra_")

    bitcoin = annual_metrics_for_returns(
        combined["timestamp"],
        combined["bitcoin_return"],
        combined["buy_and_hold_equity"],
    ).add_prefix("bitcoin_")

    annual = nostra.merge(
        bitcoin,
        left_on="nostra_year",
        right_on="bitcoin_year",
        validate="one_to_one",
    )

    annual = annual.rename(
        columns={
            "nostra_year": "year",
        }
    ).drop(columns=["bitcoin_year"])

    exposure_records: list[dict[str, float | int]] = []

    for year, group in combined.groupby(
        combined["timestamp"].dt.year,
        sort=True,
    ):
        exposure = group["nostra_exposure"].astype(float)
        turnover = group["turnover"].astype(float)

        exposure_records.append(
            {
                "year": int(year),
                "exposure_mean": float(exposure.mean()),
                "absolute_exposure_mean": float(
                    exposure.abs().mean()
                ),
                "exposure_minimum": float(exposure.min()),
                "exposure_maximum": float(exposure.max()),
                "turnover": float(turnover.sum()),
                "modeled_cost_rate_sum": float(
                    turnover.sum() * cost_bps / 10000.0
                ),
                "positive_exposure_share": float(
                    (exposure > 0).mean()
                ),
                "negative_exposure_share": float(
                    (exposure < 0).mean()
                ),
                "zero_exposure_share": float(
                    np.isclose(exposure, 0.0).mean()
                ),
            }
        )

    exposure_table = pd.DataFrame(exposure_records)

    annual = annual.merge(
        exposure_table,
        on="year",
        validate="one_to_one",
    )

    annual["active_return"] = (
        annual["nostra_return"]
        - annual["bitcoin_return"]
    )

    annual["volatility_reduction"] = (
        annual["bitcoin_annualized_volatility"]
        - annual["nostra_annualized_volatility"]
    )

    annual["drawdown_reduction"] = (
        annual["nostra_maximum_drawdown"]
        - annual["bitcoin_maximum_drawdown"]
    )

    annual["partial_period"] = annual["year"].isin(
        [2020, 2026]
    )

    return annual


def build_all_strategy_annual_returns(
    combined: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    strategy_equity_columns = {
        "Nostra AI V5.246": "nostra_equity",
        **{
            label: column
            for column, label in PUBLIC_LABELS.items()
        },
    }

    wide_records: list[dict[str, float | int]] = []

    for year, group in combined.groupby(
        combined["timestamp"].dt.year,
        sort=True,
    ):
        record: dict[str, float | int] = {
            "year": int(year),
        }

        for label, column in strategy_equity_columns.items():
            returns = returns_from_equity(
                combined[column]
            ).loc[group.index]

            record[label] = float(
                (1.0 + returns).prod() - 1.0
            )

        wide_records.append(record)

    wide = pd.DataFrame(wide_records)

    long = wide.melt(
        id_vars="year",
        var_name="strategy",
        value_name="calendar_return",
    )

    long["rank"] = (
        long.groupby("year")["calendar_return"]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )

    return wide, long


def format_year(year: int) -> str:
    if year in (2020, 2026):
        return f"{year}*"

    return str(year)


def plot_annual_returns(
    annual: pd.DataFrame,
    output: Path,
) -> None:
    labels = [
        format_year(int(year))
        for year in annual["year"]
    ]

    x = np.arange(len(labels))
    width = 0.36

    figure, axis = plt.subplots(
        figsize=(10.2, 5.7)
    )

    nostra_values = (
        annual["nostra_return"].to_numpy() * 100
    )
    bitcoin_values = (
        annual["bitcoin_return"].to_numpy() * 100
    )

    bars_nostra = axis.bar(
        x - width / 2,
        nostra_values,
        width,
        label="Nostra AI V5.246",
        color="#173B57",
    )

    bars_bitcoin = axis.bar(
        x + width / 2,
        bitcoin_values,
        width,
        label="Bitcoin passif",
        color="#8A949C",
    )

    axis.axhline(
        0,
        linewidth=0.8,
        color="#343A40",
    )

    axis.set_xticks(x)
    axis.set_xticklabels(labels)

    axis.set_ylabel("Rendement calendaire")
    axis.yaxis.set_major_formatter(
        PercentFormatter(xmax=100)
    )

    axis.set_title(
        "Rendements calendaires",
        loc="left",
        fontsize=15,
        fontweight="semibold",
    )

    axis.legend(
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    axis.grid(
        axis="y",
        linewidth=0.6,
        color="#E0E4E7",
    )

    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)

    for bars in (bars_nostra, bars_bitcoin):
        for bar in bars:
            height = float(bar.get_height())

            axis.annotate(
                f"{height:.1f} %".replace(".", ","),
                (
                    bar.get_x() + bar.get_width() / 2,
                    height,
                ),
                xytext=(
                    0,
                    4 if height >= 0 else -13,
                ),
                textcoords="offset points",
                ha="center",
                va="bottom" if height >= 0 else "top",
                fontsize=7.5,
            )

    figure.text(
        0.08,
        0.015,
        "* Période partielle. Rendements nets des coûts "
        "modélisés, calculés par composition des observations "
        "quotidiennes.",
        fontsize=7.8,
        color="#626B72",
    )

    figure.tight_layout(rect=(0.04, 0.055, 0.99, 0.99))

    output.parent.mkdir(parents=True, exist_ok=True)

    figure.savefig(
        output,
        dpi=320,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(figure)


def plot_annual_risk(
    annual: pd.DataFrame,
    output: Path,
) -> None:
    labels = [
        format_year(int(year))
        for year in annual["year"]
    ]

    x = np.arange(len(labels))
    width = 0.36

    figure, axes = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(10.2, 8.0),
        sharex=True,
    )

    nostra_color = "#173B57"
    bitcoin_color = "#8A949C"

    axis = axes[0]

    axis.bar(
        x - width / 2,
        annual["nostra_annualized_volatility"] * 100,
        width,
        label="Nostra AI V5.246",
        color=nostra_color,
    )

    axis.bar(
        x + width / 2,
        annual["bitcoin_annualized_volatility"] * 100,
        width,
        label="Bitcoin passif",
        color=bitcoin_color,
    )

    axis.set_ylabel("Volatilité annualisée")
    axis.yaxis.set_major_formatter(
        PercentFormatter(xmax=100)
    )

    axis.set_title(
        "A. Volatilité par année calendaire",
        loc="left",
        fontsize=12,
        fontweight="semibold",
    )

    axis.legend(
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    axis = axes[1]

    axis.bar(
        x - width / 2,
        annual["nostra_maximum_drawdown"] * 100,
        width,
        color=nostra_color,
    )

    axis.bar(
        x + width / 2,
        annual["bitcoin_maximum_drawdown"] * 100,
        width,
        color=bitcoin_color,
    )

    axis.axhline(
        0,
        linewidth=0.8,
        color="#343A40",
    )

    axis.set_ylabel("Perte maximale calendaire")
    axis.yaxis.set_major_formatter(
        PercentFormatter(xmax=100)
    )

    axis.set_title(
        "B. Perte maximale par année calendaire",
        loc="left",
        fontsize=12,
        fontweight="semibold",
    )

    axis.set_xticks(x)
    axis.set_xticklabels(labels)

    for axis in axes:
        axis.grid(
            axis="y",
            linewidth=0.6,
            color="#E0E4E7",
        )

        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    figure.text(
        0.08,
        0.015,
        "* Période partielle. Les pertes maximales sont "
        "calculées sur une courbe rebased à 1 au début de "
        "chaque période calendaire.",
        fontsize=7.8,
        color="#626B72",
    )

    figure.subplots_adjust(
        left=0.10,
        right=0.985,
        top=0.98,
        bottom=0.09,
        hspace=0.32,
    )

    output.parent.mkdir(parents=True, exist_ok=True)

    figure.savefig(
        output,
        dpi=320,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(figure)


def plot_annual_exposure_turnover(
    annual: pd.DataFrame,
    output: Path,
) -> None:
    labels = [
        format_year(int(year))
        for year in annual["year"]
    ]

    x = np.arange(len(labels))
    width = 0.36

    figure, axes = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(10.2, 7.8),
        sharex=True,
    )

    axis = axes[0]

    axis.bar(
        x - width / 2,
        annual["exposure_mean"] * 100,
        width,
        label="Exposition moyenne",
        color="#173B57",
    )

    axis.bar(
        x + width / 2,
        annual["absolute_exposure_mean"] * 100,
        width,
        label="Exposition absolue moyenne",
        color="#5D8792",
    )

    axis.set_ylabel("Exposition")
    axis.yaxis.set_major_formatter(
        PercentFormatter(xmax=100)
    )

    axis.set_title(
        "A. Exposition moyenne par année",
        loc="left",
        fontsize=12,
        fontweight="semibold",
    )

    axis.legend(
        frameon=False,
        ncol=2,
        loc="upper left",
    )

    axis = axes[1]

    bars = axis.bar(
        x,
        annual["turnover"],
        width=0.56,
        color="#7D8992",
    )

    axis.set_ylabel("Unités d’exposition")
    axis.set_title(
        "B. Rotation annuelle",
        loc="left",
        fontsize=12,
        fontweight="semibold",
    )

    axis.set_xticks(x)
    axis.set_xticklabels(labels)

    for bar in bars:
        height = float(bar.get_height())

        axis.annotate(
            f"{height:.2f}".replace(".", ","),
            (
                bar.get_x() + bar.get_width() / 2,
                height,
            ),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
        )

    for axis in axes:
        axis.grid(
            axis="y",
            linewidth=0.6,
            color="#E0E4E7",
        )

        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    figure.text(
        0.08,
        0.015,
        "* Période partielle. La rotation inclut le "
        "mouvement initial depuis une exposition nulle.",
        fontsize=7.8,
        color="#626B72",
    )

    figure.subplots_adjust(
        left=0.10,
        right=0.985,
        top=0.98,
        bottom=0.09,
        hspace=0.32,
    )

    output.parent.mkdir(parents=True, exist_ok=True)

    figure.savefig(
        output,
        dpi=320,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(figure)


def plot_strategy_heatmap(
    wide: pd.DataFrame,
    combined: pd.DataFrame,
    output: Path,
) -> None:
    strategy_columns = [
        column
        for column in wide.columns
        if column != "year"
    ]

    overall_cagrs: dict[str, float] = {}

    mapping = {
        "Nostra AI V5.246": "nostra_equity",
        **{
            label: column
            for column, label in PUBLIC_LABELS.items()
        },
    }

    for label, equity_column in mapping.items():
        final_equity = float(
            combined[equity_column].iloc[-1]
        )

        overall_cagrs[label] = (
            final_equity
            ** (
                ANNUALIZATION_FACTOR
                / EXPECTED_OBSERVATIONS
            )
            - 1.0
        )

    ordered = sorted(
        strategy_columns,
        key=lambda label: overall_cagrs[label],
        reverse=True,
    )

    matrix = (
        wide.set_index("year")[ordered]
        .transpose()
        .to_numpy(dtype=float)
        * 100
    )

    years = [
        format_year(int(year))
        for year in wide["year"]
    ]

    max_abs = max(
        abs(float(np.nanmin(matrix))),
        abs(float(np.nanmax(matrix))),
    )

    norm = TwoSlopeNorm(
        vmin=-max_abs,
        vcenter=0,
        vmax=max_abs,
    )

    figure, axis = plt.subplots(
        figsize=(10.5, 7.4)
    )

    image = axis.imshow(
        matrix,
        aspect="auto",
        cmap="RdBu",
        norm=norm,
    )

    axis.set_xticks(np.arange(len(years)))
    axis.set_xticklabels(years)

    axis.set_yticks(np.arange(len(ordered)))
    axis.set_yticklabels(ordered)

    axis.set_title(
        "Rendements calendaires des douze stratégies",
        loc="left",
        fontsize=14,
        fontweight="semibold",
        pad=14,
    )

    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = float(
                matrix[row_index, column_index]
            )

            axis.text(
                column_index,
                row_index,
                f"{value:.1f} %".replace(".", ","),
                ha="center",
                va="center",
                fontsize=7.2,
                color=(
                    "white"
                    if abs(value) > max_abs * 0.48
                    else "#20262B"
                ),
            )

    colorbar = figure.colorbar(
        image,
        ax=axis,
        fraction=0.025,
        pad=0.025,
    )

    colorbar.ax.yaxis.set_major_formatter(
        PercentFormatter(xmax=100)
    )

    axis.tick_params(
        axis="both",
        length=0,
        labelsize=8.5,
    )

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_visible(False)
    axis.spines["bottom"].set_visible(False)

    figure.text(
        0.19,
        0.015,
        "* Période partielle. Classement des lignes selon "
        "le CAGR obtenu sur l’ensemble de la période.",
        fontsize=7.8,
        color="#626B72",
    )

    figure.tight_layout(rect=(0.02, 0.05, 0.99, 0.99))

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
            "Produit les agrégats et figures annuels "
            "nécessaires à la Partie V du rapport."
        )
    )

    parser.add_argument(
        "--private-input",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--public-curves",
        type=Path,
        default=Path(
            "artifacts/releases/v0.2.1/"
            "baseline_daily_curves.csv"
        ),
    )

    parser.add_argument(
        "--private-date-column",
        default="timestamp",
    )

    parser.add_argument(
        "--private-equity-column",
        default="v5246_equity_25bps",
    )

    parser.add_argument(
        "--private-position-column",
        default="v5246_position",
    )

    parser.add_argument(
        "--cost-bps",
        type=float,
        default=25.0,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "artifacts/report_support/part_v"
        ),
    )

    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=Path(
            "docs/figures"
        ),
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    private_path = (
        arguments.private_input.expanduser().resolve()
    )

    public_path = (
        arguments.public_curves.expanduser().resolve()
    )

    output_dir = (
        arguments.output_dir.expanduser().resolve()
    )

    figures_dir = (
        arguments.figures_dir.expanduser().resolve()
    )

    private = load_private(
        private_path,
        arguments.private_date_column,
        arguments.private_equity_column,
        arguments.private_position_column,
    )

    public = load_public(public_path)

    combined = public.merge(
        private,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )

    validate_dates(combined)

    combined["bitcoin_return"] = returns_from_equity(
        combined["buy_and_hold_equity"]
    )

    annual_core = build_core_annual_table(
        combined,
        arguments.cost_bps,
    )

    annual_wide, annual_long = (
        build_all_strategy_annual_returns(combined)
    )

    annual_ranks = annual_long[
        annual_long["strategy"] == "Nostra AI V5.246"
    ][
        [
            "year",
            "rank",
        ]
    ].rename(
        columns={
            "rank": "nostra_rank_among_12",
        }
    )

    annual_core = annual_core.merge(
        annual_ranks,
        on="year",
        validate="one_to_one",
    )

    best_public_records = []

    for year, group in annual_long.groupby(
        "year",
        sort=True,
    ):
        public_group = group[
            group["strategy"] != "Nostra AI V5.246"
        ].sort_values(
            "calendar_return",
            ascending=False,
        )

        best = public_group.iloc[0]

        best_public_records.append(
            {
                "year": int(year),
                "best_public_strategy": str(
                    best["strategy"]
                ),
                "best_public_return": float(
                    best["calendar_return"]
                ),
            }
        )

    annual_core = annual_core.merge(
        pd.DataFrame(best_public_records),
        on="year",
        validate="one_to_one",
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    figures_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    annual_core_path = (
        output_dir
        / "part_v_annual_nostra_vs_bitcoin.csv"
    )

    annual_wide_path = (
        output_dir
        / "part_v_annual_all_strategies.csv"
    )

    annual_long_path = (
        output_dir
        / "part_v_annual_all_strategies_long.csv"
    )

    summary_path = (
        output_dir
        / "part_v_annual_summary.json"
    )

    annual_core.to_csv(
        annual_core_path,
        index=False,
    )

    annual_wide.to_csv(
        annual_wide_path,
        index=False,
    )

    annual_long.to_csv(
        annual_long_path,
        index=False,
    )

    summary = {
        "schema_version": 1,
        "analysis": "part_v_annual_decomposition",
        "period": {
            "start": str(EXPECTED_START),
            "end": str(EXPECTED_END),
            "observations": EXPECTED_OBSERVATIONS,
        },
        "sources": {
            "private_input_sha256": sha256_file(
                private_path
            ),
            "public_curves_sha256": sha256_file(
                public_path
            ),
        },
        "reconciliations": {
            "nostra_final_equity": float(
                combined["nostra_equity"].iloc[-1]
            ),
            "bitcoin_final_equity": float(
                combined[
                    "buy_and_hold_equity"
                ].iloc[-1]
            ),
            "turnover_total": float(
                combined["turnover"].sum()
            ),
            "exposure_mean": float(
                combined["nostra_exposure"].mean()
            ),
            "absolute_exposure_mean": float(
                combined[
                    "nostra_exposure"
                ].abs().mean()
            ),
            "exposure_minimum": float(
                combined["nostra_exposure"].min()
            ),
            "exposure_maximum": float(
                combined["nostra_exposure"].max()
            ),
        },
        "annual_records": annual_core.to_dict(
            orient="records"
        ),
    }

    summary_path.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    plot_annual_returns(
        annual_core,
        figures_dir
        / "figure_5_5_calendar_returns.png",
    )

    plot_annual_risk(
        annual_core,
        figures_dir
        / "figure_5_6_calendar_risk.png",
    )

    plot_annual_exposure_turnover(
        annual_core,
        figures_dir
        / "figure_5_7_annual_exposure_turnover.png",
    )

    plot_strategy_heatmap(
        annual_wide,
        combined,
        figures_dir
        / "figure_5_3b_calendar_strategy_heatmap.png",
    )

    display_columns = [
        "year",
        "nostra_observations",
        "nostra_return",
        "bitcoin_return",
        "active_return",
        "nostra_annualized_volatility",
        "bitcoin_annualized_volatility",
        "nostra_maximum_drawdown",
        "bitcoin_maximum_drawdown",
        "exposure_mean",
        "absolute_exposure_mean",
        "turnover",
        "nostra_rank_among_12",
        "best_public_strategy",
        "best_public_return",
    ]

    display = annual_core[display_columns].copy()

    percentage_columns = [
        "nostra_return",
        "bitcoin_return",
        "active_return",
        "nostra_annualized_volatility",
        "bitcoin_annualized_volatility",
        "nostra_maximum_drawdown",
        "bitcoin_maximum_drawdown",
        "exposure_mean",
        "absolute_exposure_mean",
        "best_public_return",
    ]

    for column in percentage_columns:
        display[column] = display[column] * 100

    print()
    print("=== TABLE ANNUELLE PRINCIPALE ===")
    print(
        display.to_string(
            index=False,
            formatters={
                column: (
                    lambda value: f"{value:.4f} %"
                )
                for column in percentage_columns
            },
        )
    )

    print()
    print("=== RÉCONCILIATION GLOBALE ===")
    print(
        "Capital final Nostra : "
        f"{combined['nostra_equity'].iloc[-1]:.12f}"
    )
    print(
        "Capital final bitcoin : "
        f"{combined['buy_and_hold_equity'].iloc[-1]:.12f}"
    )
    print(
        "Exposition moyenne : "
        f"{combined['nostra_exposure'].mean() * 100:.8f} %"
    )
    print(
        "Exposition absolue moyenne : "
        f"{combined['nostra_exposure'].abs().mean() * 100:.8f} %"
    )
    print(
        "Rotation cumulée : "
        f"{combined['turnover'].sum():.12f}"
    )

    print()
    print("=== FICHIERS PRODUITS ===")
    print(annual_core_path)
    print(annual_wide_path)
    print(annual_long_path)
    print(summary_path)

    print()
    print("=== FIGURES PRODUITES ===")
    print(
        figures_dir
        / "figure_5_3b_calendar_strategy_heatmap.png"
    )
    print(
        figures_dir
        / "figure_5_5_calendar_returns.png"
    )
    print(
        figures_dir
        / "figure_5_6_calendar_risk.png"
    )
    print(
        figures_dir
        / "figure_5_7_annual_exposure_turnover.png"
    )

    print()
    print("=== EMPREINTES SOURCES ===")
    print(
        "Privé : "
        f"{sha256_file(private_path)}"
    )
    print(
        "Public : "
        f"{sha256_file(public_path)}"
    )


if __name__ == "__main__":
    main()
