#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MultipleLocator

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_CURVES = ROOT / "artifacts" / "releases" / "v0.2.1" / "baseline_daily_curves.csv"

SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_v"

FIGURES_DIR = ROOT / "docs" / "figures"
TABLES_DIR = ROOT / "docs" / "tables"

OUTPUT_JSON = SUPPORT_DIR / "part_v_institutional_metrics.json"

OUTPUT_MARKDOWN = TABLES_DIR / "part_v_institutional_metrics.md"

OUTPUT_FIGURE = FIGURES_DIR / "figure_5_6b_rolling_36m_volatility.png"

EXPECTED_OBSERVATIONS = 2211

EXPECTED_PRIVATE_SHA256 = "056e13af2b26b0e449e502bf814db1a6a396f90aa4cb2bae74b2771ce8285c2e"

EXPECTED_PUBLIC_SHA256 = "4cdd65f8b27c97c42ebc30fb7974024bf11af3cd1e5eea85e39b4c3fa7310d0d"

AS_OF = pd.Timestamp(
    "2026-06-02",
    tz="UTC",
)

INCEPTION = pd.Timestamp(
    "2020-05-14",
    tz="UTC",
)

NOSTRA_COLOR = "#1f77b4"
BITCOIN_COLOR = "#ff7f0e"
GRID_COLOR = "#d9d9d9"
AXIS_COLOR = "#777777"
TEXT_COLOR = "#222222"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Generate the remaining institutional metrics for Part V.")
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


def format_percent(
    value: float,
    decimals: int = 2,
) -> str:
    return f"{value * 100:.{decimals}f}".replace(".", ",") + " %"


def format_points(
    value: float,
    decimals: int = 2,
) -> str:
    return f"{value * 100:+.{decimals}f}".replace(".", ",") + " pts"


def format_number(
    value: float,
    decimals: int = 3,
) -> str:
    return f"{value:.{decimals}f}".replace(
        ".",
        ",",
    )


def load_data(
    private_path: Path,
) -> pd.DataFrame:
    private_path = private_path.resolve()

    if sha256_file(private_path) != EXPECTED_PRIVATE_SHA256:
        raise ValueError("Empreinte de la source privée non conforme.")

    if sha256_file(PUBLIC_CURVES) != EXPECTED_PUBLIC_SHA256:
        raise ValueError("Empreinte des courbes publiques non conforme.")

    private = pd.read_csv(private_path)

    required_private = {
        "timestamp",
        "v5246_equity_25bps",
    }

    missing_private = required_private.difference(private.columns)

    if missing_private:
        raise ValueError("Colonnes privées absentes : " + ", ".join(sorted(missing_private)))

    private = private[
        [
            "timestamp",
            "v5246_equity_25bps",
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

    private = private[
        [
            "timestamp",
            "nostra_equity",
        ]
    ]

    public = pd.read_csv(PUBLIC_CURVES)

    public["timestamp"] = pd.to_datetime(
        public["timestamp"],
        utc=True,
        errors="raise",
    ).dt.normalize()

    public["bitcoin_equity"] = pd.to_numeric(
        public["buy_and_hold_equity"],
        errors="raise",
    )

    public = public[
        [
            "timestamp",
            "bitcoin_equity",
        ]
    ]

    data = private.merge(
        public,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )

    data = data.sort_values("timestamp").reset_index(drop=True)

    if len(data) != EXPECTED_OBSERVATIONS:
        raise ValueError(f"{EXPECTED_OBSERVATIONS} observations attendues, {len(data)} obtenues.")

    if data.isna().any().any():
        raise ValueError("Valeurs manquantes après réconciliation.")

    if data["timestamp"].iloc[0] != INCEPTION:
        raise ValueError("Date initiale non conforme.")

    if data["timestamp"].iloc[-1] != AS_OF:
        raise ValueError("Date finale non conforme.")

    if (
        (
            data[
                [
                    "nostra_equity",
                    "bitcoin_equity",
                ]
            ]
            <= 0
        )
        .any()
        .any()
    ):
        raise ValueError("Capital nul ou négatif détecté.")

    return data


def daily_returns(
    equity: pd.Series,
) -> pd.Series:
    returns = equity.pct_change()

    returns.iloc[0] = equity.iloc[0] - 1.0

    return returns.astype(float)


def monthly_returns(
    data: pd.DataFrame,
) -> pd.DataFrame:
    month_keys = data["timestamp"].dt.strftime("%Y-%m")

    monthly = (
        data.groupby(
            month_keys,
            sort=True,
            group_keys=False,
        )
        .tail(1)
        .copy()
        .reset_index(drop=True)
    )

    monthly["nostra_return"] = monthly["nostra_equity"].pct_change()

    monthly["bitcoin_return"] = monthly["bitcoin_equity"].pct_change()

    monthly.loc[
        0,
        "nostra_return",
    ] = monthly.loc[0, "nostra_equity"] - 1.0

    monthly.loc[
        0,
        "bitcoin_return",
    ] = monthly.loc[0, "bitcoin_equity"] - 1.0

    return monthly[
        [
            "timestamp",
            "nostra_return",
            "bitcoin_return",
        ]
    ]


def anchor_value(
    data: pd.DataFrame,
    column: str,
    requested_date: pd.Timestamp,
) -> tuple[pd.Timestamp, float]:
    eligible = data[data["timestamp"] <= requested_date]

    if eligible.empty:
        raise ValueError(f"Aucune observation disponible avant {requested_date}.")

    row = eligible.iloc[-1]

    return (
        pd.Timestamp(row["timestamp"]),
        float(row[column]),
    )


def horizon_record(
    data: pd.DataFrame,
    *,
    name: str,
    requested_anchor: pd.Timestamp | None,
    annualized: bool,
    inception_base: bool = False,
) -> dict[str, Any]:
    if inception_base:
        anchor_timestamp = INCEPTION
        nostra_initial = 1.0
        bitcoin_initial = 1.0
    else:
        if requested_anchor is None:
            raise ValueError("Ancre manquante pour l'horizon.")

        (
            anchor_timestamp,
            nostra_initial,
        ) = anchor_value(
            data,
            "nostra_equity",
            requested_anchor,
        )

        (
            bitcoin_anchor_timestamp,
            bitcoin_initial,
        ) = anchor_value(
            data,
            "bitcoin_equity",
            requested_anchor,
        )

        if bitcoin_anchor_timestamp != anchor_timestamp:
            raise ValueError("Ancres Nostra et bitcoin différentes.")

    nostra_final = float(data["nostra_equity"].iloc[-1])

    bitcoin_final = float(data["bitcoin_equity"].iloc[-1])

    nostra_growth = nostra_final / nostra_initial

    bitcoin_growth = bitcoin_final / bitcoin_initial

    elapsed_days = int((AS_OF - anchor_timestamp).days)

    if annualized:
        annualization_denominator = len(data) if inception_base else elapsed_days

        if annualization_denominator <= 0:
            raise ValueError("Dénominateur non positif pour annualisation.")

        exponent = 365.0 / annualization_denominator

        nostra_return = nostra_growth**exponent - 1.0

        bitcoin_return = bitcoin_growth**exponent - 1.0
    else:
        nostra_return = nostra_growth - 1.0
        bitcoin_return = bitcoin_growth - 1.0

    return {
        "horizon": name,
        "requested_anchor": (
            None if requested_anchor is None else requested_anchor.date().isoformat()
        ),
        "effective_anchor": (anchor_timestamp.date().isoformat()),
        "as_of": AS_OF.date().isoformat(),
        "elapsed_days": elapsed_days,
        "annualized": annualized,
        "nostra_return": float(nostra_return),
        "bitcoin_return": float(bitcoin_return),
        "active_return": float(nostra_return - bitcoin_return),
    }


def calculate_horizons(
    data: pd.DataFrame,
) -> list[dict[str, Any]]:
    return [
        horizon_record(
            data,
            name="2026 YTD",
            requested_anchor=pd.Timestamp(
                "2025-12-31",
                tz="UTC",
            ),
            annualized=False,
        ),
        horizon_record(
            data,
            name="1 an",
            requested_anchor=(AS_OF - pd.DateOffset(years=1)),
            annualized=False,
        ),
        horizon_record(
            data,
            name="3 ans annualisés",
            requested_anchor=(AS_OF - pd.DateOffset(years=3)),
            annualized=True,
        ),
        horizon_record(
            data,
            name="5 ans annualisés",
            requested_anchor=(AS_OF - pd.DateOffset(years=5)),
            annualized=True,
        ),
        horizon_record(
            data,
            name="Depuis l'origine annualisé",
            requested_anchor=None,
            annualized=True,
            inception_base=True,
        ),
        horizon_record(
            data,
            name="Depuis l'origine cumulé",
            requested_anchor=None,
            annualized=False,
            inception_base=True,
        ),
    ]


def geometric_annualized_return(
    returns: pd.Series,
    periods_per_year: float,
) -> float:
    values = returns.to_numpy(dtype=float)

    if len(values) == 0:
        raise ValueError("Aucun rendement pour annualisation.")

    growth = float(np.prod(1.0 + values))

    return float(growth ** (periods_per_year / len(values)) - 1.0)


def calculate_relative_metrics(
    data: pd.DataFrame,
    monthly: pd.DataFrame,
) -> dict[str, Any]:
    nostra = daily_returns(data["nostra_equity"]).to_numpy(dtype=float)

    bitcoin = daily_returns(data["bitcoin_equity"]).to_numpy(dtype=float)

    active = nostra - bitcoin

    correlation = float(np.corrcoef(nostra, bitcoin)[0, 1])

    covariance = float(
        np.cov(
            nostra,
            bitcoin,
            ddof=1,
        )[0, 1]
    )

    bitcoin_variance = float(
        np.var(
            bitcoin,
            ddof=1,
        )
    )

    beta = covariance / bitcoin_variance

    tracking_error = float(
        np.std(
            active,
            ddof=1,
        )
        * math.sqrt(365.0)
    )

    annualized_active_mean = float(np.mean(active) * 365.0)

    information_ratio = annualized_active_mean / tracking_error

    up_mask = monthly["bitcoin_return"] > 0

    down_mask = monthly["bitcoin_return"] < 0

    nostra_up = geometric_annualized_return(
        monthly.loc[
            up_mask,
            "nostra_return",
        ],
        12.0,
    )

    bitcoin_up = geometric_annualized_return(
        monthly.loc[
            up_mask,
            "bitcoin_return",
        ],
        12.0,
    )

    nostra_down = geometric_annualized_return(
        monthly.loc[
            down_mask,
            "nostra_return",
        ],
        12.0,
    )

    bitcoin_down = geometric_annualized_return(
        monthly.loc[
            down_mask,
            "bitcoin_return",
        ],
        12.0,
    )

    return {
        "daily_observations": len(data),
        "monthly_observations": len(monthly),
        "daily_correlation": correlation,
        "daily_beta": float(beta),
        "tracking_error_annualized": tracking_error,
        "information_ratio": float(information_ratio),
        "upside_capture_ratio": float(nostra_up / bitcoin_up),
        "downside_capture_ratio": float(nostra_down / bitcoin_down),
        "capture_frequency": "monthly",
        "tracking_error_annualization": 365,
    }


def calculate_rolling_volatility(
    monthly: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rolling = monthly.copy()

    rolling["nostra_volatility_36m"] = rolling["nostra_return"].rolling(
        window=36,
        min_periods=36,
    ).std(ddof=1) * math.sqrt(12.0)

    rolling["bitcoin_volatility_36m"] = rolling["bitcoin_return"].rolling(
        window=36,
        min_periods=36,
    ).std(ddof=1) * math.sqrt(12.0)

    valid = rolling.dropna(
        subset=[
            "nostra_volatility_36m",
            "bitcoin_volatility_36m",
        ]
    ).copy()

    if valid.empty:
        raise ValueError("Historique insuffisant pour 36 mois.")

    year_end = (
        valid.groupby(
            valid["timestamp"].dt.year,
            sort=True,
            group_keys=False,
        )
        .tail(1)
        .copy()
    )

    records = []

    for _, row in year_end.iterrows():
        records.append(
            {
                "date": (pd.Timestamp(row["timestamp"]).date().isoformat()),
                "nostra_volatility_36m": float(row["nostra_volatility_36m"]),
                "bitcoin_volatility_36m": float(row["bitcoin_volatility_36m"]),
            }
        )

    latest = valid.iloc[-1]

    summary = {
        "method": ("Annualized standard deviation of 36 monthly net returns"),
        "window_months": 36,
        "annualization_factor": 12,
        "first_available_date": (pd.Timestamp(valid["timestamp"].iloc[0]).date().isoformat()),
        "latest_date": (pd.Timestamp(latest["timestamp"]).date().isoformat()),
        "latest_nostra_volatility": float(latest["nostra_volatility_36m"]),
        "latest_bitcoin_volatility": float(latest["bitcoin_volatility_36m"]),
        "year_end_records": records,
    }

    return valid, summary


def generate_rolling_figure(
    rolling: pd.DataFrame,
) -> None:
    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure, axis = plt.subplots(figsize=(10.5, 5.6))

    axis.plot(
        rolling["timestamp"],
        rolling["nostra_volatility_36m"] * 100,
        color=NOSTRA_COLOR,
        linewidth=1.6,
        label="Nostra AI V5.246",
    )

    axis.plot(
        rolling["timestamp"],
        rolling["bitcoin_volatility_36m"] * 100,
        color=BITCOIN_COLOR,
        linewidth=1.5,
        label="Bitcoin passif",
    )

    axis.set_axisbelow(True)

    axis.grid(
        axis="y",
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

    axis.set_ylabel("Volatilité annualisée glissante (36 mois)")

    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _position: f"{value:.0f} %"))

    axis.yaxis.set_major_locator(MultipleLocator(10))

    axis.xaxis.set_major_locator(mdates.YearLocator())

    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    axis.set_ylim(
        bottom=0,
    )

    axis.legend(
        frameon=False,
        ncols=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.08),
    )

    figure.tight_layout()

    figure.savefig(
        OUTPUT_FIGURE,
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(figure)


def write_metrics_json(
    horizons: list[dict[str, Any]],
    relative: dict[str, Any],
    rolling_summary: dict[str, Any],
) -> None:
    SUPPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "schema_version": 1,
        "analysis": ("part_v_institutional_completion"),
        "model": "Nostra AI V5.246",
        "period": {
            "start": INCEPTION.date().isoformat(),
            "end": AS_OF.date().isoformat(),
            "observations": EXPECTED_OBSERVATIONS,
        },
        "sources": {
            "private_input_sha256": (EXPECTED_PRIVATE_SHA256),
            "public_curves_sha256": (EXPECTED_PUBLIC_SHA256),
        },
        "performance_horizons": horizons,
        "relative_to_bitcoin": relative,
        "rolling_36_month_volatility": (rolling_summary),
    }

    OUTPUT_JSON.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_markdown(
    horizons: list[dict[str, Any]],
    relative: dict[str, Any],
    rolling_summary: dict[str, Any],
) -> None:
    TABLES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    horizon_lines = [
        "## Tableau 5.1 - Performance par horizon",
        "",
        "| Horizon | Nostra AI V5.246 | Bitcoin passif | Écart actif |",
        "|---|---:|---:|---:|",
    ]

    for record in horizons:
        horizon_lines.append(
            "| "
            + str(record["horizon"])
            + " | "
            + format_percent(float(record["nostra_return"]))
            + " | "
            + format_percent(float(record["bitcoin_return"]))
            + " | "
            + format_points(float(record["active_return"]))
            + " |"
        )

    relative_lines = [
        "",
        "## Tableau 5.3 - Mesures relatives au bitcoin",
        "",
        "| Mesure | Valeur |",
        "|---|---:|",
        (
            "| Corrélation quotidienne | "
            + format_number(float(relative["daily_correlation"]))
            + " |"
        ),
        ("| Bêta quotidien réalisé | " + format_number(float(relative["daily_beta"])) + " |"),
        (
            "| Tracking error annualisée | "
            + format_percent(float(relative["tracking_error_annualized"]))
            + " |"
        ),
        ("| Information ratio | " + format_number(float(relative["information_ratio"])) + " |"),
        (
            "| Capture des hausses mensuelles | "
            + format_percent(
                float(relative["upside_capture_ratio"]),
                decimals=1,
            )
            + " |"
        ),
        (
            "| Capture des baisses mensuelles | "
            + format_percent(
                float(relative["downside_capture_ratio"]),
                decimals=1,
            )
            + " |"
        ),
    ]

    rolling_lines = [
        "",
        "## Figure 5.6b - Volatilité glissante sur 36 mois",
        "",
        ("Volatilité annualisée calculée sur 36 rendements mensuels nets successifs."),
        "",
        ("- Dernière observation : " + str(rolling_summary["latest_date"])),
        (
            "- Nostra AI V5.246 : "
            + format_percent(float(rolling_summary["latest_nostra_volatility"]))
        ),
        (
            "- Bitcoin passif : "
            + format_percent(float(rolling_summary["latest_bitcoin_volatility"]))
        ),
    ]

    disclosure_lines = [
        "",
        "## Note de présentation obligatoire",
        "",
        (
            "Les résultats présentés sont issus "
            "d'une évaluation historique "
            "rétrospective de Nostra AI V5.246. "
            "Ils ne constituent pas la performance "
            "d'un portefeuille client, d'un fonds "
            "ou d'un composite de mandats "
            "effectivement gérés."
        ),
        "",
        (
            "Les rendements intègrent un décalage "
            "causal d'une observation et des coûts "
            "de transaction modélisés de 25 points "
            "de base par unité de rotation. Ils "
            "n'intègrent pas de frais de licence, "
            "de gestion, de distribution, de "
            "fiscalité ou de coûts propres à "
            "l'infrastructure d'un partenaire."
        ),
        "",
        (
            "Les périodes 2020 et 2026 sont "
            "partielles et ne sont pas annualisées "
            "dans les comparaisons calendaires. "
            "HilmarCorp ne revendique aucune "
            "conformité aux standards GIPS."
        ),
        "",
        (
            "Les performances passées, simulées "
            "ou rétrospectives ne préjugent pas "
            "des résultats futurs."
        ),
    ]

    OUTPUT_MARKDOWN.write_text(
        "\n".join(
            [
                "# Compléments institutionnels de la Partie V",
                "",
                *horizon_lines,
                *relative_lines,
                *rolling_lines,
                *disclosure_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )


def update_manifest() -> None:
    manifest_path = SUPPORT_DIR / "manifest.json"

    checksum_path = SUPPORT_DIR / "SHA256SUMS"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    existing_paths = {str(record["path"]) for record in manifest["files"]}

    existing_paths.update(
        {
            OUTPUT_JSON.relative_to(ROOT).as_posix(),
            OUTPUT_MARKDOWN.relative_to(ROOT).as_posix(),
            OUTPUT_FIGURE.relative_to(ROOT).as_posix(),
            Path(__file__).resolve().relative_to(ROOT).as_posix(),
        }
    )

    records = []

    for relative in sorted(existing_paths):
        path = ROOT / relative

        if not path.is_file():
            raise FileNotFoundError(f"Fichier du manifeste absent : {relative}")

        records.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest["files"] = records

    manifest["status"] = (
        "Figures et agrégats quantitatifs "
        "institutionnels dérivés à partir "
        "des entrées gelées de l'évaluation."
    )

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
        "".join(f"{record['sha256']}  {record['path']}\n" for record in records),
        encoding="utf-8",
    )


def main() -> None:
    arguments = parse_args()

    data = load_data(arguments.private_input)

    monthly = monthly_returns(data)

    horizons = calculate_horizons(data)

    relative = calculate_relative_metrics(
        data,
        monthly,
    )

    (
        rolling,
        rolling_summary,
    ) = calculate_rolling_volatility(monthly)

    generate_rolling_figure(rolling)

    write_metrics_json(
        horizons,
        relative,
        rolling_summary,
    )

    write_markdown(
        horizons,
        relative,
        rolling_summary,
    )

    update_manifest()

    print("PASS_PART_V_INSTITUTIONAL_COMPLETION")

    print(OUTPUT_JSON.relative_to(ROOT))

    print(OUTPUT_MARKDOWN.relative_to(ROOT))

    print(OUTPUT_FIGURE.relative_to(ROOT))


if __name__ == "__main__":
    main()
