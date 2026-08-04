#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator, MultipleLocator

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_CURVES = ROOT / "artifacts" / "releases" / "v0.2.1" / "baseline_daily_curves.csv"

SUMMARY = ROOT / "artifacts" / "report_support" / "part_v" / "part_v_annual_summary.json"

SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_v"
FIGURES_DIR = ROOT / "docs" / "figures"

EXPECTED_OBSERVATIONS = 2211
EXPECTED_PRIVATE_SHA256 = "056e13af2b26b0e449e502bf814db1a6a396f90aa4cb2bae74b2771ce8285c2e"
EXPECTED_PUBLIC_SHA256 = "4cdd65f8b27c97c42ebc30fb7974024bf11af3cd1e5eea85e39b4c3fa7310d0d"

NOSTRA_COLOR = "#1f77b4"
BITCOIN_COLOR = "#ff7f0e"
THIRD_COLOR = "#7f7f7f"
REFERENCE_COLOR = "#7f7f7f"
GRID_COLOR = "#d9d9d9"
AXIS_COLOR = "#777777"
TEXT_COLOR = "#222222"

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate the complete Part V quantitative figure set."
    )

    parser.add_argument(
        "--private-input",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def percentage_axis(value: float, _position: int) -> str:
    return f"{value:.0f} %"


def multiple_axis(value: float, _position: int) -> str:
    if value >= 10:
        text = f"{value:.0f}"
    elif value >= 1:
        text = f"{value:.1f}"
    else:
        text = f"{value:.2f}"

    return text + "\u00d7"


def style_axis(
    axis: plt.Axes,
    *,
    grid_axis: str = "y",
    percentage: bool = False,
    zero_line: bool = False,
) -> None:
    axis.set_facecolor("white")
    axis.set_axisbelow(True)

    axis.grid(
        axis=grid_axis,
        color=GRID_COLOR,
        linewidth=0.7,
    )

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)

    axis.spines["left"].set_color(AXIS_COLOR)
    axis.spines["bottom"].set_color(AXIS_COLOR)

    axis.tick_params(
        axis="both",
        colors=TEXT_COLOR,
        labelsize=9,
    )

    if percentage:
        axis.yaxis.set_major_formatter(FuncFormatter(percentage_axis))

    if zero_line:
        axis.axhline(
            0,
            color="#555555",
            linewidth=0.9,
        )


def save_figure(
    figure: plt.Figure,
    filename: str,
) -> Path:
    output = FIGURES_DIR / filename

    figure.savefig(
        output,
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(figure)

    return output


def load_inputs(
    private_path: Path,
) -> tuple[pd.DataFrame, dict]:
    if sha256_file(private_path) != EXPECTED_PRIVATE_SHA256:
        raise ValueError("Empreinte du fichier privé non conforme.")

    if sha256_file(PUBLIC_CURVES) != EXPECTED_PUBLIC_SHA256:
        raise ValueError("Empreinte des courbes publiques non conforme.")

    private = pd.read_csv(private_path)

    required_private = {
        "timestamp",
        "v5246_equity_25bps",
        "v5246_position",
    }

    missing_private = required_private.difference(private.columns)

    if missing_private:
        raise ValueError("Colonnes privées absentes : " + ", ".join(sorted(missing_private)))

    private = private[
        [
            "timestamp",
            "v5246_equity_25bps",
            "v5246_position",
        ]
    ].copy()

    private["timestamp"] = pd.to_datetime(
        private["timestamp"],
        utc=True,
        errors="raise",
    ).dt.normalize()

    private["nostra_equity"] = pd.to_numeric(
        private["v5246_equity_25bps"],
        errors="raise",
    )

    private["nostra_position"] = pd.to_numeric(
        private["v5246_position"],
        errors="raise",
    )

    private = private[
        [
            "timestamp",
            "nostra_equity",
            "nostra_position",
        ]
    ]

    public = pd.read_csv(PUBLIC_CURVES)

    public["timestamp"] = pd.to_datetime(
        public["timestamp"],
        utc=True,
        errors="raise",
    ).dt.normalize()

    public_columns = list(PUBLIC_LABELS)

    missing_public = set(public_columns).difference(public.columns)

    if missing_public:
        raise ValueError("Courbes publiques absentes : " + ", ".join(sorted(missing_public)))

    public = public[
        [
            "timestamp",
            *public_columns,
        ]
    ].copy()

    data = public.merge(
        private,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )

    data = data.sort_values("timestamp").reset_index(drop=True)

    if len(data) != EXPECTED_OBSERVATIONS:
        raise ValueError(f"{EXPECTED_OBSERVATIONS} observations attendues, {len(data)} obtenues.")

    if data.isna().any().any():
        raise ValueError("Valeurs manquantes après réconciliation.")

    data["turnover"] = data["nostra_position"].diff().fillna(data["nostra_position"]).abs()

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    expected_turnover = float(summary["reconciliations"]["turnover_total"])

    observed_turnover = float(data["turnover"].sum())

    if not np.isclose(
        observed_turnover,
        expected_turnover,
        atol=1e-10,
        rtol=0,
    ):
        raise ValueError(
            "Rotation totale non réconciliée : "
            f"{observed_turnover:.12f} contre "
            f"{expected_turnover:.12f}."
        )

    return data, summary


def month_end_sample(
    data: pd.DataFrame,
) -> pd.DataFrame:
    month_keys = data["timestamp"].dt.strftime("%Y-%m")

    month_ends = data.groupby(
        month_keys,
        sort=True,
        group_keys=False,
    ).tail(1)

    return (
        pd.concat(
            [
                data.iloc[[0]],
                month_ends,
                data.iloc[[-1]],
            ],
            ignore_index=True,
        )
        .drop_duplicates("timestamp")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


def annual_returns(
    timestamps: pd.Series,
    equity: pd.Series,
) -> pd.Series:
    returns = equity.pct_change()

    returns.iloc[0] = equity.iloc[0] - 1.0

    frame = pd.DataFrame(
        {
            "year": timestamps.dt.year,
            "return": returns,
        }
    )

    return frame.groupby("year")["return"].apply(
        lambda values: float(np.prod(1.0 + values.to_numpy()) - 1.0)
    )


def generate_figure_52(
    data: pd.DataFrame,
) -> Path:
    sampled = month_end_sample(data)

    figure, axis = plt.subplots(figsize=(11.2, 5.6))

    axis.plot(
        sampled["timestamp"],
        sampled["nostra_equity"],
        color=NOSTRA_COLOR,
        linewidth=1.6,
        label="Nostra AI V5.246",
    )

    axis.plot(
        sampled["timestamp"],
        sampled["buy_and_hold_equity"],
        color=BITCOIN_COLOR,
        linewidth=1.4,
        label="Bitcoin passif",
    )

    style_axis(axis)

    axis.set_ylabel("Capital cumule net (base 1)")

    axis.yaxis.set_major_formatter(FuncFormatter(multiple_axis))

    axis.xaxis.set_major_locator(mdates.YearLocator())

    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    axis.set_xlim(
        sampled["timestamp"].min(),
        sampled["timestamp"].max(),
    )

    maximum = float(
        sampled[
            [
                "nostra_equity",
                "buy_and_hold_equity",
            ]
        ]
        .max()
        .max()
    )

    axis.set_ylim(
        0,
        maximum * 1.06,
    )

    axis.legend(
        frameon=False,
        ncols=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.09),
    )

    figure.tight_layout()

    return save_figure(
        figure,
        "figure_5_2_nostra_vs_bitcoin_passif.png",
    )


def generate_figure_53(
    data: pd.DataFrame,
) -> Path:
    sampled = month_end_sample(data)

    figure, axes = plt.subplots(
        4,
        3,
        figsize=(11.5, 10.5),
        sharex=True,
        sharey=True,
    )

    flat_axes = axes.ravel()

    maximum = float(
        sampled[
            [
                "nostra_equity",
                *PUBLIC_LABELS,
            ]
        ]
        .max()
        .max()
    )

    for index, (
        column,
        label,
    ) in enumerate(PUBLIC_LABELS.items()):
        axis = flat_axes[index]

        axis.plot(
            sampled["timestamp"],
            sampled["nostra_equity"],
            color=NOSTRA_COLOR,
            linewidth=1.35,
        )

        axis.plot(
            sampled["timestamp"],
            sampled[column],
            color=BITCOIN_COLOR,
            linewidth=1.15,
        )

        style_axis(axis)

        axis.set_title(
            label,
            fontsize=9,
            loc="left",
        )

        axis.set_ylim(
            0,
            maximum * 1.04,
        )

        axis.yaxis.set_major_formatter(FuncFormatter(multiple_axis))

        axis.xaxis.set_major_locator(mdates.YearLocator(2))

        axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    flat_axes[-1].axis("off")

    figure.legend(
        handles=[
            Line2D(
                [0],
                [0],
                color=NOSTRA_COLOR,
                linewidth=1.6,
                label="Nostra AI V5.246",
            ),
            Line2D(
                [0],
                [0],
                color=BITCOIN_COLOR,
                linewidth=1.4,
                label="Strategie de reference",
            ),
        ],
        frameon=False,
        ncols=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
    )

    figure.subplots_adjust(
        left=0.07,
        right=0.99,
        top=0.95,
        bottom=0.06,
        hspace=0.30,
        wspace=0.18,
    )

    return save_figure(
        figure,
        "figure_5_3_nostra_vs_11_references.png",
    )


def generate_figure_53b(
    data: pd.DataFrame,
    summary: dict,
) -> Path:
    strategy_series = {
        "Nostra AI V5.246": annual_returns(
            data["timestamp"],
            data["nostra_equity"],
        )
    }

    for column, label in PUBLIC_LABELS.items():
        strategy_series[label] = annual_returns(
            data["timestamp"],
            data[column],
        )

    annual = pd.DataFrame(strategy_series)

    years = list(annual.index)

    partial_years = {
        int(record["year"])
        for record in summary["annual_records"]
        if bool(record["partial_period"])
    }

    year_labels = [f"{year}{'*' if year in partial_years else ''}" for year in years]

    strategy_labels = list(strategy_series)

    matrix = annual[strategy_labels].transpose().to_numpy(dtype=float)

    maximum = max(
        float(np.abs(matrix).max()),
        0.01,
    )

    figure, axis = plt.subplots(figsize=(11.3, 7.2))

    image = axis.imshow(
        matrix,
        aspect="auto",
        cmap="RdBu",
        vmin=-maximum,
        vmax=maximum,
    )

    axis.set_xticks(np.arange(len(year_labels)))

    axis.set_xticklabels(year_labels)

    axis.set_yticks(np.arange(len(strategy_labels)))

    axis.set_yticklabels(
        strategy_labels,
        fontsize=8.5,
    )

    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]

            axis.text(
                column,
                row,
                f"{value * 100:.0f} %",
                ha="center",
                va="center",
                fontsize=7.5,
                color=("white" if abs(value) > maximum * 0.55 else TEXT_COLOR),
            )

    axis.tick_params(
        length=0,
        colors=TEXT_COLOR,
    )

    for spine in axis.spines.values():
        spine.set_visible(False)

    colorbar = figure.colorbar(
        image,
        ax=axis,
        fraction=0.025,
        pad=0.025,
    )

    colorbar.ax.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _position: f"{value * 100:.0f} %")
    )

    figure.tight_layout()

    return save_figure(
        figure,
        "figure_5_3b_calendar_strategy_heatmap.png",
    )


def generate_figure_54(
    data: pd.DataFrame,
) -> Path:
    working = data[
        [
            "timestamp",
            "nostra_position",
            "turnover",
        ]
    ].copy()

    working["month"] = working["timestamp"].dt.strftime("%Y-%m")

    monthly = (
        working.groupby(
            "month",
            sort=True,
        )
        .agg(
            timestamp=("timestamp", "max"),
            signed_exposure=(
                "nostra_position",
                "mean",
            ),
            turnover=("turnover", "sum"),
        )
        .reset_index(drop=True)
    )

    absolute_monthly = (
        working.assign(absolute_exposure=working["nostra_position"].abs())
        .groupby(
            "month",
            sort=True,
        )["absolute_exposure"]
        .mean()
        .to_numpy()
    )

    monthly["absolute_exposure"] = absolute_monthly

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(11.2, 6.8),
        sharex=True,
        gridspec_kw={
            "height_ratios": [2, 1],
        },
    )

    exposure_axis, turnover_axis = axes

    exposure_axis.plot(
        monthly["timestamp"],
        monthly["signed_exposure"] * 100,
        color=NOSTRA_COLOR,
        linewidth=1.45,
        label="Exposition moyenne",
    )

    exposure_axis.plot(
        monthly["timestamp"],
        monthly["absolute_exposure"] * 100,
        color=BITCOIN_COLOR,
        linewidth=1.35,
        label="Exposition absolue moyenne",
    )

    style_axis(
        exposure_axis,
        percentage=True,
        zero_line=True,
    )

    exposure_axis.set_ylabel("Exposition")

    exposure_axis.legend(
        frameon=False,
        ncols=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.12),
    )

    turnover_axis.bar(
        monthly["timestamp"],
        monthly["turnover"],
        width=20,
        color=THIRD_COLOR,
    )

    style_axis(turnover_axis)

    turnover_axis.set_ylabel("Rotation")
    turnover_axis.set_xlabel("Date")

    turnover_axis.xaxis.set_major_locator(mdates.YearLocator())

    turnover_axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    figure.tight_layout()

    return save_figure(
        figure,
        "figure_5_4_exposition_absolue_rotation.png",
    )


def annual_arrays(
    summary: dict,
) -> dict[str, np.ndarray | list[str]]:
    records = summary["annual_records"]

    labels = [f"{record['year']}{'*' if record['partial_period'] else ''}" for record in records]

    return {
        "labels": labels,
        "nostra_return": np.array([record["nostra_return"] * 100 for record in records]),
        "bitcoin_return": np.array([record["bitcoin_return"] * 100 for record in records]),
        "nostra_volatility": np.array(
            [record["nostra_annualized_volatility"] * 100 for record in records]
        ),
        "bitcoin_volatility": np.array(
            [record["bitcoin_annualized_volatility"] * 100 for record in records]
        ),
        "nostra_drawdown": np.array(
            [record["nostra_maximum_drawdown"] * 100 for record in records]
        ),
        "bitcoin_drawdown": np.array(
            [record["bitcoin_maximum_drawdown"] * 100 for record in records]
        ),
        "signed_exposure": np.array([record["exposure_mean"] * 100 for record in records]),
        "absolute_exposure": np.array(
            [record["absolute_exposure_mean"] * 100 for record in records]
        ),
        "turnover": np.array([record["turnover"] for record in records]),
    }


def generate_figure_55(
    arrays: dict[str, np.ndarray | list[str]],
) -> Path:
    labels = arrays["labels"]
    nostra = arrays["nostra_return"]
    bitcoin = arrays["bitcoin_return"]

    assert isinstance(labels, list)
    assert isinstance(nostra, np.ndarray)
    assert isinstance(bitcoin, np.ndarray)

    positions = np.arange(len(labels))
    width = 0.36

    figure, axis = plt.subplots(figsize=(10.5, 5.6))

    axis.bar(
        positions - width / 2,
        nostra,
        width,
        color=NOSTRA_COLOR,
        label="Nostra AI V5.246",
    )

    axis.bar(
        positions + width / 2,
        bitcoin,
        width,
        color=BITCOIN_COLOR,
        label="Bitcoin passif",
    )

    style_axis(
        axis,
        percentage=True,
        zero_line=True,
    )

    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel("Rendement calendaire")

    axis.yaxis.set_major_locator(MultipleLocator(50))

    axis.legend(
        frameon=False,
        ncols=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.08),
    )

    figure.tight_layout()

    return save_figure(
        figure,
        "figure_5_5_calendar_returns.png",
    )


def generate_figure_56(
    arrays: dict[str, np.ndarray | list[str]],
) -> Path:
    labels = arrays["labels"]
    nostra_volatility = arrays["nostra_volatility"]
    bitcoin_volatility = arrays["bitcoin_volatility"]
    nostra_drawdown = arrays["nostra_drawdown"]
    bitcoin_drawdown = arrays["bitcoin_drawdown"]

    assert isinstance(labels, list)
    assert isinstance(
        nostra_volatility,
        np.ndarray,
    )
    assert isinstance(
        bitcoin_volatility,
        np.ndarray,
    )
    assert isinstance(
        nostra_drawdown,
        np.ndarray,
    )
    assert isinstance(
        bitcoin_drawdown,
        np.ndarray,
    )

    positions = np.arange(len(labels))
    width = 0.36

    figure, axes = plt.subplots(
        1,
        2,
        figsize=(12.5, 5.6),
    )

    volatility_axis, drawdown_axis = axes

    volatility_axis.bar(
        positions - width / 2,
        nostra_volatility,
        width,
        color=NOSTRA_COLOR,
        label="Nostra AI V5.246",
    )

    volatility_axis.bar(
        positions + width / 2,
        bitcoin_volatility,
        width,
        color=BITCOIN_COLOR,
        label="Bitcoin passif",
    )

    style_axis(
        volatility_axis,
        percentage=True,
    )

    volatility_axis.set_xticks(positions)
    volatility_axis.set_xticklabels(labels)
    volatility_axis.set_ylabel("Volatilite annualisee")
    volatility_axis.set_title(
        "Volatilite annualisee",
        fontsize=11,
    )

    volatility_axis.yaxis.set_major_locator(MultipleLocator(10))

    drawdown_axis.bar(
        positions - width / 2,
        nostra_drawdown,
        width,
        color=NOSTRA_COLOR,
    )

    drawdown_axis.bar(
        positions + width / 2,
        bitcoin_drawdown,
        width,
        color=BITCOIN_COLOR,
    )

    style_axis(
        drawdown_axis,
        percentage=True,
        zero_line=True,
    )

    drawdown_axis.set_xticks(positions)
    drawdown_axis.set_xticklabels(labels)
    drawdown_axis.set_ylabel("Perte maximale")
    drawdown_axis.set_title(
        "Perte maximale",
        fontsize=11,
    )

    drawdown_axis.yaxis.set_major_locator(MultipleLocator(10))

    figure.legend(
        handles=[
            Line2D(
                [0],
                [0],
                color=NOSTRA_COLOR,
                linewidth=7,
                label="Nostra AI V5.246",
            ),
            Line2D(
                [0],
                [0],
                color=BITCOIN_COLOR,
                linewidth=7,
                label="Bitcoin passif",
            ),
        ],
        frameon=False,
        ncols=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.02),
    )

    figure.tight_layout(rect=(0, 0, 1, 0.94))

    return save_figure(
        figure,
        "figure_5_6_calendar_risk.png",
    )


def generate_figure_57(
    arrays: dict[str, np.ndarray | list[str]],
) -> Path:
    labels = arrays["labels"]
    signed = arrays["signed_exposure"]
    absolute = arrays["absolute_exposure"]
    turnover = arrays["turnover"]

    assert isinstance(labels, list)
    assert isinstance(signed, np.ndarray)
    assert isinstance(absolute, np.ndarray)
    assert isinstance(turnover, np.ndarray)

    positions = np.arange(len(labels))
    width = 0.36

    figure, axes = plt.subplots(
        1,
        2,
        figsize=(12.5, 5.6),
    )

    exposure_axis, turnover_axis = axes

    exposure_axis.bar(
        positions - width / 2,
        signed,
        width,
        color=NOSTRA_COLOR,
        label="Exposition moyenne",
    )

    exposure_axis.bar(
        positions + width / 2,
        absolute,
        width,
        color=BITCOIN_COLOR,
        label="Exposition absolue moyenne",
    )

    style_axis(
        exposure_axis,
        percentage=True,
        zero_line=True,
    )

    exposure_axis.set_xticks(positions)
    exposure_axis.set_xticklabels(labels)
    exposure_axis.set_ylabel("Exposition")
    exposure_axis.set_title(
        "Exposition annuelle",
        fontsize=11,
    )

    exposure_axis.yaxis.set_major_locator(MultipleLocator(10))

    exposure_axis.legend(
        frameon=False,
        fontsize=8.5,
        ncols=2,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.12),
    )

    turnover_axis.bar(
        positions,
        turnover,
        width=0.58,
        color=THIRD_COLOR,
    )

    style_axis(turnover_axis)

    turnover_axis.set_xticks(positions)
    turnover_axis.set_xticklabels(labels)
    turnover_axis.set_ylabel("Unites d'exposition")
    turnover_axis.set_title(
        "Rotation annuelle",
        fontsize=11,
    )

    turnover_axis.yaxis.set_major_locator(MaxNLocator(integer=False))

    figure.tight_layout(rect=(0, 0, 1, 0.94))

    return save_figure(
        figure,
        "figure_5_7_annual_exposure_turnover.png",
    )


def update_manifest(
    generated: list[Path],
) -> None:
    tracked_paths = [
        SUMMARY,
        *generated,
        Path(__file__).resolve(),
    ]

    files = []

    for path in tracked_paths:
        relative = path.relative_to(ROOT)

        files.append(
            {
                "path": relative.as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest = {
        "schema_version": 1,
        "package": "part_v_report_support",
        "model": "Nostra AI V5.246",
        "period": {
            "start": "2020-05-14",
            "end": "2026-06-02",
            "observations": EXPECTED_OBSERVATIONS,
        },
        "status": (
            "Figures quantitatives harmonisees a partir des entrees gelees de l'evaluation."
        ),
        "files": files,
    }

    manifest_path = SUPPORT_DIR / "manifest.json"
    checksum_path = SUPPORT_DIR / "SHA256SUMS"

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    checksum_path.write_text(
        "".join(f"{record['sha256']}  {record['path']}\n" for record in files),
        encoding="utf-8",
    )


def main() -> None:
    arguments = parse_args()

    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    data, summary = load_inputs(arguments.private_input.resolve())

    arrays = annual_arrays(summary)

    generated = [
        generate_figure_52(data),
        generate_figure_53(data),
        generate_figure_53b(data, summary),
        generate_figure_54(data),
        generate_figure_55(arrays),
        generate_figure_56(arrays),
        generate_figure_57(arrays),
    ]

    update_manifest(generated)

    print("PASS_PART_V_QUANT_FIGURE_REGENERATION")

    for path in generated:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
