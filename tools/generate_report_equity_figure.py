#!/usr/bin/env python3
"""Génère la figure 5.2 du rapport public.

La série quotidienne de Nostra AI est lue depuis un fichier privé local.
Le script ne publie ni la série source ni un export tabulaire dérivé.

La figure publique utilise uniquement :
- la première observation ;
- les observations de fin de mois ;
- la dernière observation.

La sortie autorisée est exclusivement un fichier PNG rasterisé.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from pathlib import Path

import pandas as pd

try:
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
except ImportError as exc:
    raise SystemExit(
        "Matplotlib est requis. Exécuter : "
        "python -m pip install -r requirements/figures.txt"
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PUBLIC_INPUT = (
    REPO_ROOT
    / "artifacts"
    / "releases"
    / "v0.2.1"
    / "baseline_daily_curves.csv"
)

DEFAULT_OUTPUT = (
    REPO_ROOT
    / "docs"
    / "figures"
    / "figure_5_2_nostra_vs_bitcoin_passif.png"
)

EXPECTED_START = pd.Timestamp("2020-05-14", tz="UTC")
EXPECTED_END = pd.Timestamp("2026-06-02", tz="UTC")

EXPECTED_NOSTRA_FINAL = 12.863641976380386
EXPECTED_BITCOIN_FINAL = 7.212950328296465

DATE_CANDIDATES = (
    "timestamp",
    "date",
    "datetime",
    "time",
)

EQUITY_CANDIDATES = (
    "nostra_equity",
    "equity",
    "equity_curve",
    "portfolio_equity",
    "portfolio_value",
    "capital",
    "nav",
    "value",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Génère une figure rasterisée comparant le capital de Nostra AI "
            "à celui d'une exposition passive au bitcoin."
        )
    )

    parser.add_argument(
        "--nostra-input",
        type=Path,
        required=True,
        help="Chemin du CSV privé contenant la date et le capital de Nostra AI.",
    )

    parser.add_argument(
        "--public-input",
        type=Path,
        default=DEFAULT_PUBLIC_INPUT,
        help="Courbes publiques de référence.",
    )

    parser.add_argument(
        "--nostra-date-column",
        default=None,
        help="Nom de la colonne de date du fichier privé.",
    )

    parser.add_argument(
        "--nostra-equity-column",
        default=None,
        help="Nom de la colonne de capital du fichier privé.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Fichier PNG de sortie.",
    )

    parser.add_argument(
        "--linear",
        action="store_true",
        help="Utiliser une échelle linéaire au lieu de l'échelle logarithmique.",
    )

    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def resolve_column(
    columns: list[str],
    explicit_name: str | None,
    candidates: tuple[str, ...],
    description: str,
) -> str:
    if explicit_name is not None:
        if explicit_name not in columns:
            raise ValueError(
                f"Colonne {description} absente : {explicit_name!r}. "
                f"Colonnes disponibles : {columns}"
            )
        return explicit_name

    by_lowercase = {column.lower(): column for column in columns}

    for candidate in candidates:
        if candidate.lower() in by_lowercase:
            return by_lowercase[candidate.lower()]

    raise ValueError(
        f"Impossible d'identifier automatiquement la colonne {description}. "
        f"Colonnes disponibles : {columns}. "
        f"Utiliser l'option correspondante en ligne de commande."
    )


def load_equity_series(
    path: Path,
    output_column: str,
    date_column: str | None = None,
    equity_column: str | None = None,
) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    source = pd.read_csv(path)

    if source.empty:
        raise ValueError(f"Le fichier est vide : {path}")

    columns = list(source.columns)

    resolved_date_column = resolve_column(
        columns,
        date_column,
        DATE_CANDIDATES,
        "de date",
    )

    resolved_equity_column = resolve_column(
        columns,
        equity_column,
        EQUITY_CANDIDATES,
        "de capital",
    )

    timestamps = pd.to_datetime(
        source[resolved_date_column],
        utc=True,
        errors="raise",
    ).dt.normalize()

    equities = pd.to_numeric(
        source[resolved_equity_column],
        errors="raise",
    )

    result = pd.DataFrame(
        {
            "timestamp": timestamps,
            output_column: equities,
        }
    )

    if result.isna().any().any():
        raise ValueError(f"Valeurs manquantes détectées dans {path}")

    if result["timestamp"].duplicated().any():
        duplicates = result.loc[
            result["timestamp"].duplicated(keep=False),
            "timestamp",
        ].astype(str)

        raise ValueError(
            "Dates dupliquées détectées : "
            + ", ".join(duplicates.head(10).tolist())
        )

    if (result[output_column] <= 0).any():
        raise ValueError(
            f"La série {output_column} contient un capital nul ou négatif."
        )

    return result.sort_values("timestamp").reset_index(drop=True)


def assert_close(
    label: str,
    observed: float,
    expected: float,
    tolerance: float = 1e-6,
) -> None:
    if not math.isclose(
        observed,
        expected,
        rel_tol=0,
        abs_tol=tolerance,
    ):
        raise ValueError(
            f"{label} non réconcilié : valeur observée {observed:.12f}, "
            f"valeur attendue {expected:.12f}."
        )


def select_month_end_observations(data: pd.DataFrame) -> pd.DataFrame:
    month_keys = data["timestamp"].dt.strftime("%Y-%m")

    month_ends = (
        data.groupby(month_keys, sort=True, group_keys=False)
        .tail(1)
        .copy()
    )

    sampled = pd.concat(
        [
            data.iloc[[0]],
            month_ends,
            data.iloc[[-1]],
        ],
        ignore_index=True,
    )

    return (
        sampled.drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


def format_factor(value: float, _position: int) -> str:
    if value >= 10:
        text = f"{value:.0f}"
    elif value >= 1:
        text = f"{value:.1f}"
    else:
        text = f"{value:.2f}"

    return text.replace(".", ",") + "×"


def format_decimal(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def generate_figure(
    data: pd.DataFrame,
    output: Path,
    linear_scale: bool,
) -> None:
    output = output.resolve()

    if output.suffix.lower() != ".png":
        raise ValueError(
            "La figure publique doit être produite exclusivement au format PNG."
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    figure, axis = plt.subplots(figsize=(11.2, 5.8))

    nostra_color = "#151515"
    bitcoin_color = "#858585"

    axis.plot(
        data["timestamp"],
        data["nostra_equity"],
        label="Nostra AI V5.246",
        linewidth=1.25,
        color=nostra_color,
        solid_capstyle="round",
        zorder=3,
    )

    axis.plot(
        data["timestamp"],
        data["buy_and_hold_equity"],
        label="Bitcoin passif",
        linewidth=1.0,
        color=bitcoin_color,
        linestyle=(0, (4, 2)),
        solid_capstyle="round",
        zorder=2,
    )

    if linear_scale:
        axis.set_ylabel("Capital cumulé net, base 1")
        axis.set_ylim(
            bottom=0,
            top=float(
                data[
                    ["nostra_equity", "buy_and_hold_equity"]
                ].max().max()
            ) * 1.06,
        )
    else:
        axis.set_yscale("log")
        axis.set_ylabel("Capital cumulé net, base 1, échelle logarithmique")

    axis.yaxis.set_major_formatter(FuncFormatter(format_factor))

    axis.xaxis.set_major_locator(mdates.YearLocator())
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    axis.set_xlim(
        data["timestamp"].min(),
        data["timestamp"].max(),
    )

    axis.grid(
        visible=True,
        which="major",
        axis="y",
        linewidth=0.65,
        color="#D7D7D7",
        alpha=0.75,
    )

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)

    axis.spines["left"].set_color("#555555")
    axis.spines["bottom"].set_color("#555555")

    axis.tick_params(
        axis="both",
        colors="#333333",
        labelsize=9,
    )

    axis.legend(
        loc="upper left",
        frameon=False,
        fontsize=9,
        handlelength=3.0,
    )

    scale_note = (
        "échelle linéaire"
        if linear_scale
        else "échelle logarithmique"
    )

    figure.text(
        0.075,
        0.018,
        "2 211 observations quotidiennes | capital initial 1 | "
        "coûts de 25 pb par unité de rotation | "
        "décalage causal d’une observation | "
        f"{scale_note} | 14 mai 2020–2 juin 2026",
        fontsize=7.8,
        color="#5F5F5F",
    )

    figure.tight_layout(rect=(0.055, 0.055, 0.995, 0.985))

    figure.savefig(
        output,
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
        metadata={
            "Title": (
                "Figure 5.2 - Capital quotidien de Nostra AI "
                "et du bitcoin passif"
            ),
            "Author": "HilmarCorp SAS",
            "Description": (
                "Comparaison sur les 2 211 observations quotidiennes "
                "du protocole officiel."
            ),
        },
    )

    plt.close(figure)


def main() -> int:
    args = parse_args()

    public_series = load_equity_series(
        path=args.public_input,
        output_column="buy_and_hold_equity",
        date_column="timestamp",
        equity_column="buy_and_hold_equity",
    )

    nostra_series = load_equity_series(
        path=args.nostra_input,
        output_column="nostra_equity",
        date_column=args.nostra_date_column,
        equity_column=args.nostra_equity_column,
    )

    public_series = public_series.loc[
        public_series["timestamp"].between(
            EXPECTED_START,
            EXPECTED_END,
        )
    ].copy()

    nostra_series = nostra_series.loc[
        nostra_series["timestamp"].between(
            EXPECTED_START,
            EXPECTED_END,
        )
    ].copy()

    combined = public_series.merge(
        nostra_series,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )

    if combined.empty:
        raise ValueError("Aucune date commune entre les deux séries.")

    if combined["timestamp"].iloc[0] != EXPECTED_START:
        raise ValueError(
            "La première date commune n'est pas le 14 mai 2020."
        )

    if combined["timestamp"].iloc[-1] != EXPECTED_END:
        raise ValueError(
            "La dernière date commune n'est pas le 2 juin 2026."
        )

    if len(combined) != 2211:
        raise ValueError(
            f"Nombre d'observations non réconcilié : "
            f"{len(combined)} au lieu de 2 211."
        )

    assert_close(
        "Capital final de Nostra AI",
        float(combined["nostra_equity"].iloc[-1]),
        EXPECTED_NOSTRA_FINAL,
    )

    assert_close(
        "Capital final du bitcoin passif",
        float(combined["buy_and_hold_equity"].iloc[-1]),
        EXPECTED_BITCOIN_FINAL,
    )

    plotted = combined.copy()

    generate_figure(
        data=plotted,
        output=args.output,
        linear_scale=args.linear,
    )

    print(f"Figure générée : {args.output.resolve()}")
    print(f"Observations quotidiennes réconciliées : {len(combined)}")
    print(f"Observations affichées : {len(plotted)}")
    print(
        "SHA-256 du fichier privé utilisé : "
        f"{sha256_file(args.nostra_input)}"
    )
    print(
        "Capital final Nostra AI : "
        f"{combined['nostra_equity'].iloc[-1]:.12f}"
    )
    print(
        "Capital final bitcoin passif : "
        f"{combined['buy_and_hold_equity'].iloc[-1]:.12f}"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
