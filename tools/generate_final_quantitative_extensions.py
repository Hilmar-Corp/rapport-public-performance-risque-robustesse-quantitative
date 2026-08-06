#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CURVES = ROOT / "artifacts" / "releases" / "v0.2.1" / "baseline_daily_curves.csv"

PART_V_DIR = ROOT / "artifacts" / "report_support" / "part_v_extension"
PART_VII_DIR = ROOT / "artifacts" / "report_support" / "part_vii_extension"
FIGURES_DIR = ROOT / "docs" / "figures"
TABLES_DIR = ROOT / "docs" / "tables"

PART_V_SUMMARY = PART_V_DIR / "part_v_final_extension_summary.json"
PART_VII_SUMMARY = PART_VII_DIR / "part_vii_entry_rolling_summary.json"
PART_V_TABLE = TABLES_DIR / "part_v_final_extension_results.md"
PART_VII_TABLE = TABLES_DIR / "part_vii_entry_rolling_results.md"

FIGURE_5_8 = FIGURES_DIR / "figure_5_8_matched_bitcoin_comparators.png"
FIGURE_5_9 = FIGURES_DIR / "figure_5_9_return_concentration.png"
FIGURE_5_10 = FIGURES_DIR / "figure_5_10_economic_attribution.png"
FIGURE_7_7 = FIGURES_DIR / "figure_7_7_start_date_sensitivity.png"
FIGURE_7_8 = FIGURES_DIR / "figure_7_8_rolling_horizon_performance.png"

GENERATOR_PATH = ROOT / "tools" / "generate_final_quantitative_extensions.py"

EXPECTED_PRIVATE_SHA256 = "056e13af2b26b0e449e502bf814db1a6a396f90aa4cb2bae74b2771ce8285c2e"
EXPECTED_PUBLIC_SHA256 = "4cdd65f8b27c97c42ebc30fb7974024bf11af3cd1e5eea85e39b4c3fa7310d0d"
EXPECTED_OBSERVATIONS = 2211
EXPECTED_START = pd.Timestamp("2020-05-14", tz="UTC")
EXPECTED_END = pd.Timestamp("2026-06-02", tz="UTC")
EXPECTED_NOSTRA_FINAL = 12.863641976380386
EXPECTED_BITCOIN_FINAL = 7.212950328296465
EXPECTED_TURNOVER = 46.79247585

ANNUALIZATION = 365.0
COST_BPS = 25.0
COST_RATE = COST_BPS / 10_000.0
ROLLING_HORIZONS = (30, 90, 365, 730, 1095)
CONCENTRATION_COUNTS = (5, 10, 20)

NOSTRA_COLOR = "#173B57"
BITCOIN_COLOR = "#8A949C"
MATCHED_COLOR = "#5D8792"
RISK_MATCHED_COLOR = "#A47D4E"
GRID_COLOR = "#E0E4E7"
TEXT_COLOR = "#222222"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Génère les extensions quantitatives finales des Parties V et VII.")
    )
    parser.add_argument("--private-input", type=Path, required=True)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def returns_from_equity(equity: pd.Series) -> pd.Series:
    returns = equity.astype(float).pct_change()
    returns.iloc[0] = float(equity.iloc[0]) - 1.0
    require(np.isfinite(returns.to_numpy(dtype=float)).all(), "Rendements invalides.")
    return returns.astype(float)


def equity_from_returns(returns: np.ndarray) -> np.ndarray:
    require(np.all(np.isfinite(returns)), "Rendements non finis.")
    require(np.all(returns > -1.0), "Un rendement est inférieur ou égal à -100 %.")
    return np.cumprod(1.0 + returns)


def maximum_drawdown(returns: np.ndarray) -> float:
    equity = equity_from_returns(returns)
    running_max = np.maximum.accumulate(np.concatenate((np.array([1.0]), equity)))[1:]
    return float(np.min(equity / running_max - 1.0))


def metrics(returns: np.ndarray) -> dict[str, float | int]:
    observations = len(returns)
    require(observations >= 2, "Deux observations au minimum sont requises.")
    equity = equity_from_returns(returns)
    final_equity = float(equity[-1])
    volatility_daily = float(np.std(returns, ddof=1))
    annualized_volatility = volatility_daily * math.sqrt(ANNUALIZATION)
    sharpe = (
        float(np.mean(returns)) / volatility_daily * math.sqrt(ANNUALIZATION)
        if volatility_daily > 0.0
        else 0.0
    )
    return {
        "observations": observations,
        "final_equity": final_equity,
        "total_return": final_equity - 1.0,
        "cagr": final_equity ** (ANNUALIZATION / observations) - 1.0,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "maximum_drawdown": maximum_drawdown(returns),
    }


def constant_exposure_returns(
    raw_bitcoin_returns: np.ndarray,
    exposure: float,
    cost_rate: float = COST_RATE,
) -> np.ndarray:
    require(0.0 <= exposure <= 1.0, "L'exposition constante doit appartenir à [0, 1].")
    turnover = np.zeros(len(raw_bitcoin_returns), dtype=float)
    turnover[0] = exposure
    return exposure * raw_bitcoin_returns - cost_rate * turnover


def strategy_returns_from_cash(
    raw_bitcoin_returns: np.ndarray,
    applied_exposure: np.ndarray,
    cost_rate: float = COST_RATE,
) -> tuple[np.ndarray, np.ndarray]:
    require(
        len(raw_bitcoin_returns) == len(applied_exposure),
        "Les séries d'actif et d'exposition doivent avoir la même longueur.",
    )
    previous = np.concatenate((np.array([0.0]), applied_exposure[:-1]))
    turnover = np.abs(applied_exposure - previous)
    returns = applied_exposure * raw_bitcoin_returns - cost_rate * turnover
    return returns, turnover


def resolve_applied_exposure(
    raw_position: np.ndarray,
    raw_bitcoin_returns: np.ndarray,
    official_returns: np.ndarray,
) -> tuple[np.ndarray, str, float]:
    candidates = {
        "as_provided": raw_position,
        "one_observation_shift": np.concatenate((np.array([0.0]), raw_position[:-1])),
    }
    reconciliations: list[tuple[float, str, np.ndarray]] = []
    for name, candidate in candidates.items():
        calculated, _ = strategy_returns_from_cash(raw_bitcoin_returns, candidate)
        maximum_difference = float(np.max(np.abs(calculated - official_returns)))
        reconciliations.append((maximum_difference, name, candidate))
    reconciliations.sort(key=lambda item: item[0])
    best_difference, best_name, best_exposure = reconciliations[0]
    require(
        best_difference <= 1e-10,
        "Aucun alignement d'exposition ne réconcilie la courbe officielle. "
        f"Écart minimal : {best_difference:.3e}.",
    )
    if len(reconciliations) > 1:
        require(
            reconciliations[1][0] > 1e-8,
            "L'alignement de l'exposition est ambigu.",
        )
    return best_exposure.astype(float), best_name, best_difference


def load_data(private_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    private_path = private_path.expanduser().resolve()
    require(private_path.is_file(), f"Source privée absente : {private_path}")
    require(
        sha256_file(private_path) == EXPECTED_PRIVATE_SHA256,
        "Empreinte de la source privée non conforme.",
    )
    require(
        sha256_file(PUBLIC_CURVES) == EXPECTED_PUBLIC_SHA256,
        "Empreinte des courbes publiques non conforme.",
    )

    private = pd.read_csv(private_path)
    required_private = {
        "timestamp",
        "v5246_equity_25bps",
        "v5246_position",
    }
    missing_private = required_private.difference(private.columns)
    require(
        not missing_private,
        "Colonnes privées absentes : " + ", ".join(sorted(missing_private)),
    )
    private = private[["timestamp", "v5246_equity_25bps", "v5246_position"]].copy()
    private["timestamp"] = pd.to_datetime(
        private["timestamp"], utc=True, errors="raise"
    ).dt.normalize()
    private["nostra_equity"] = pd.to_numeric(private["v5246_equity_25bps"], errors="raise")
    private["raw_position"] = pd.to_numeric(private["v5246_position"], errors="raise")
    private = private[["timestamp", "nostra_equity", "raw_position"]]

    public = pd.read_csv(PUBLIC_CURVES)
    required_public = {
        "timestamp",
        "buy_and_hold_equity",
        "fixed_50_equity",
    }
    missing_public = required_public.difference(public.columns)
    require(
        not missing_public,
        "Colonnes publiques absentes : " + ", ".join(sorted(missing_public)),
    )
    public["timestamp"] = pd.to_datetime(
        public["timestamp"], utc=True, errors="raise"
    ).dt.normalize()
    for column in ("buy_and_hold_equity", "fixed_50_equity"):
        public[column] = pd.to_numeric(public[column], errors="raise")
    public = public[["timestamp", "buy_and_hold_equity", "fixed_50_equity"]]

    data = public.merge(
        private,
        on="timestamp",
        how="inner",
        validate="one_to_one",
    )
    data = data.sort_values("timestamp").reset_index(drop=True)

    require(len(data) == EXPECTED_OBSERVATIONS, "Nombre d'observations non conforme.")
    require(data["timestamp"].iloc[0] == EXPECTED_START, "Date initiale non conforme.")
    require(data["timestamp"].iloc[-1] == EXPECTED_END, "Date finale non conforme.")
    require(not data.isna().any().any(), "Valeurs manquantes après réconciliation.")
    require(
        abs(float(data["nostra_equity"].iloc[-1]) - EXPECTED_NOSTRA_FINAL) <= 1e-10,
        "Capital final Nostra non conforme.",
    )
    require(
        abs(float(data["buy_and_hold_equity"].iloc[-1]) - EXPECTED_BITCOIN_FINAL) <= 1e-10,
        "Capital final bitcoin non conforme.",
    )

    bitcoin_net = returns_from_equity(data["buy_and_hold_equity"]).to_numpy()
    raw_bitcoin = bitcoin_net.copy()
    raw_bitcoin[0] += COST_RATE

    fixed_50_returns = constant_exposure_returns(raw_bitcoin, 0.5)
    fixed_50_equity = equity_from_returns(fixed_50_returns)
    fixed_50_maximum_difference = float(
        np.max(np.abs(fixed_50_equity - data["fixed_50_equity"].to_numpy(dtype=float)))
    )
    require(
        fixed_50_maximum_difference <= 1e-10,
        "Le comparateur constant à 50 % n'est pas réconcilié.",
    )

    official_nostra_returns = returns_from_equity(data["nostra_equity"]).to_numpy()
    applied_exposure, alignment, exposure_difference = resolve_applied_exposure(
        data["raw_position"].to_numpy(dtype=float),
        raw_bitcoin,
        official_nostra_returns,
    )
    calculated_nostra_returns, turnover = strategy_returns_from_cash(
        raw_bitcoin,
        applied_exposure,
    )
    require(
        float(np.max(np.abs(calculated_nostra_returns - official_nostra_returns))) <= 1e-10,
        "Les rendements Nostra ne sont pas réconciliés.",
    )
    require(
        abs(float(np.sum(turnover)) - EXPECTED_TURNOVER) <= 1e-6,
        "La rotation cumulée n'est pas réconciliée.",
    )

    data["bitcoin_net_return"] = bitcoin_net
    data["raw_bitcoin_return"] = raw_bitcoin
    data["nostra_return"] = official_nostra_returns
    data["applied_exposure"] = applied_exposure
    data["turnover"] = turnover

    reconciliation = {
        "private_sha256": sha256_file(private_path),
        "public_sha256": sha256_file(PUBLIC_CURVES),
        "position_alignment": alignment,
        "maximum_return_difference": exposure_difference,
        "fixed_50_maximum_equity_difference": fixed_50_maximum_difference,
        "turnover_total": float(np.sum(turnover)),
    }
    return data, reconciliation


def solve_risk_matched_exposure(
    raw_bitcoin_returns: np.ndarray,
    target_volatility: float,
) -> float:
    low = 0.0
    high = 1.0
    for _ in range(100):
        midpoint = (low + high) / 2.0
        candidate = constant_exposure_returns(raw_bitcoin_returns, midpoint)
        volatility = float(np.std(candidate, ddof=1) * math.sqrt(ANNUALIZATION))
        if volatility < target_volatility:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def matched_comparators(data: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    raw_bitcoin = data["raw_bitcoin_return"].to_numpy(dtype=float)
    nostra_returns = data["nostra_return"].to_numpy(dtype=float)
    bitcoin_returns = data["bitcoin_net_return"].to_numpy(dtype=float)

    exposure_matched = float(data["applied_exposure"].mean())
    target_volatility = float(np.std(nostra_returns, ddof=1) * math.sqrt(ANNUALIZATION))
    risk_matched = solve_risk_matched_exposure(raw_bitcoin, target_volatility)

    series = {
        "Nostra AI V5.246": nostra_returns,
        "Bitcoin passif": bitcoin_returns,
        "Bitcoin ajusté à l'exposition": constant_exposure_returns(raw_bitcoin, exposure_matched),
        "Bitcoin ajusté au risque": constant_exposure_returns(raw_bitcoin, risk_matched),
    }

    records: list[dict[str, Any]] = []
    for label, returns in series.items():
        record: dict[str, Any] = {"strategy": label, **metrics(returns)}
        if label == "Bitcoin ajusté à l'exposition":
            record["constant_exposure"] = exposure_matched
        elif label == "Bitcoin ajusté au risque":
            record["constant_exposure"] = risk_matched
        else:
            record["constant_exposure"] = None
        records.append(record)

    return records, series


def concentration_analysis(series: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for label, returns in series.items():
        log_returns = np.log1p(returns)
        total_log_return = float(np.sum(log_returns))
        order = np.argsort(returns)
        for count in CONCENTRATION_COUNTS:
            bottom = order[:count]
            top = order[-count:]
            top_log = float(np.sum(log_returns[top]))
            bottom_log = float(np.sum(log_returns[bottom]))
            records.append(
                {
                    "strategy": label,
                    "count": count,
                    "total_log_return": total_log_return,
                    "top_log_contribution": top_log,
                    "bottom_log_contribution": bottom_log,
                    "top_share_of_total_log_return": top_log / total_log_return,
                    "bottom_share_of_total_log_return": bottom_log / total_log_return,
                    "final_equity_without_top": float(math.exp(total_log_return - top_log)),
                    "final_equity_without_bottom": float(math.exp(total_log_return - bottom_log)),
                    "final_equity_without_top_and_bottom": float(
                        math.exp(total_log_return - top_log - bottom_log)
                    ),
                }
            )
    return records


def attribution_analysis(
    data: pd.DataFrame,
    series: dict[str, np.ndarray],
) -> dict[str, Any]:
    exposure = data["applied_exposure"].to_numpy(dtype=float)
    raw_bitcoin = data["raw_bitcoin_return"].to_numpy(dtype=float)
    nostra = series["Nostra AI V5.246"]
    exposure_matched = series["Bitcoin ajusté à l'exposition"]
    turnover = data["turnover"].to_numpy(dtype=float)

    gross_returns = exposure * raw_bitcoin
    modeled_cost = COST_RATE * turnover
    require(
        float(np.max(np.abs(gross_returns - modeled_cost - nostra))) <= 1e-10,
        "La décomposition rendement brut moins coûts n'est pas réconciliée.",
    )

    total_log = float(np.sum(np.log1p(nostra)))
    buckets = [
        ("Exposition négative", exposure < 0.0),
        ("De 0 % à 25 %", (exposure >= 0.0) & (exposure < 0.25)),
        ("De 25 % à 75 %", (exposure >= 0.25) & (exposure < 0.75)),
        ("75 % et plus", exposure >= 0.75),
    ]
    exposure_records: list[dict[str, Any]] = []
    for label, mask in buckets:
        log_contribution = float(np.sum(np.log1p(nostra[mask])))
        exposure_records.append(
            {
                "bucket": label,
                "observations": int(np.sum(mask)),
                "observation_share": float(np.mean(mask)),
                "average_exposure": float(np.mean(exposure[mask])) if np.any(mask) else 0.0,
                "compounded_subsequence_return": float(math.exp(log_contribution) - 1.0),
                "log_return_contribution": log_contribution,
                "share_of_total_log_return": log_contribution / total_log,
            }
        )

    market_records: list[dict[str, Any]] = []
    for label, mask in (
        ("Jours de hausse du bitcoin", raw_bitcoin >= 0.0),
        ("Jours de baisse du bitcoin", raw_bitcoin < 0.0),
    ):
        nostra_log = float(np.sum(np.log1p(nostra[mask])))
        comparator_log = float(np.sum(np.log1p(exposure_matched[mask])))
        market_records.append(
            {
                "market_group": label,
                "observations": int(np.sum(mask)),
                "nostra_log_return_contribution": nostra_log,
                "matched_comparator_log_return_contribution": comparator_log,
                "relative_log_wealth_contribution": nostra_log - comparator_log,
            }
        )

    gross_final = float(equity_from_returns(gross_returns)[-1])
    net_final = float(equity_from_returns(nostra)[-1])
    matched_final = float(equity_from_returns(exposure_matched)[-1])

    return {
        "gross_final_equity_before_modeled_costs": gross_final,
        "net_final_equity": net_final,
        "modeled_cost_rate_sum": float(np.sum(modeled_cost)),
        "compounded_cost_drag_log_wealth": math.log(gross_final) - math.log(net_final),
        "exposure_matched_final_equity": matched_final,
        "dynamic_allocation_relative_log_wealth": math.log(net_final) - math.log(matched_final),
        "exposure_buckets": exposure_records,
        "bitcoin_direction_groups": market_records,
    }


def monthly_start_indices(timestamps: pd.Series) -> list[int]:
    month = timestamps.dt.strftime("%Y-%m")
    return [int(index) for index in month.drop_duplicates().index]


def quantile_summary(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    require(len(array) > 0, "Une distribution vide ne peut pas être résumée.")
    return {
        "minimum": float(np.min(array)),
        "p05": float(np.quantile(array, 0.05)),
        "p25": float(np.quantile(array, 0.25)),
        "median": float(np.quantile(array, 0.50)),
        "p75": float(np.quantile(array, 0.75)),
        "p95": float(np.quantile(array, 0.95)),
        "maximum": float(np.max(array)),
    }


def start_date_sensitivity(
    data: pd.DataFrame,
    exposure_matched_level: float,
) -> tuple[dict[str, Any], dict[str, list[float]]]:
    raw = data["raw_bitcoin_return"].to_numpy(dtype=float)
    exposure = data["applied_exposure"].to_numpy(dtype=float)
    indices = monthly_start_indices(data["timestamp"])

    central_records: list[dict[str, float | int]] = []
    for start in indices:
        observations = len(data) - start
        if observations < 365:
            continue
        nostra_returns, _ = strategy_returns_from_cash(raw[start:], exposure[start:])
        bitcoin_returns = constant_exposure_returns(raw[start:], 1.0)
        matched_returns = constant_exposure_returns(raw[start:], exposure_matched_level)
        nostra_metrics = metrics(nostra_returns)
        bitcoin_metrics = metrics(bitcoin_returns)
        matched_metrics = metrics(matched_returns)
        central_records.append(
            {
                "observations": observations,
                "nostra_cagr": float(nostra_metrics["cagr"]),
                "nostra_sharpe": float(nostra_metrics["sharpe"]),
                "nostra_maximum_drawdown": float(nostra_metrics["maximum_drawdown"]),
                "nostra_final_equity": float(nostra_metrics["final_equity"]),
                "bitcoin_cagr": float(bitcoin_metrics["cagr"]),
                "matched_cagr": float(matched_metrics["cagr"]),
                "outperforms_bitcoin": int(
                    float(nostra_metrics["final_equity"]) > float(bitcoin_metrics["final_equity"])
                ),
                "outperforms_matched": int(
                    float(nostra_metrics["final_equity"]) > float(matched_metrics["final_equity"])
                ),
            }
        )

    require(len(central_records) >= 40, "Nombre insuffisant de dates de départ.")
    distributions = {
        "cagr": [float(record["nostra_cagr"]) for record in central_records],
        "sharpe": [float(record["nostra_sharpe"]) for record in central_records],
        "maximum_drawdown": [
            float(record["nostra_maximum_drawdown"]) for record in central_records
        ],
        "final_equity": [float(record["nostra_final_equity"]) for record in central_records],
    }
    summary = {
        "monthly_start_count_with_at_least_365_observations": len(central_records),
        "minimum_remaining_observations": int(
            min(int(record["observations"]) for record in central_records)
        ),
        "maximum_remaining_observations": int(
            max(int(record["observations"]) for record in central_records)
        ),
        "nostra_cagr": quantile_summary(distributions["cagr"]),
        "nostra_sharpe": quantile_summary(distributions["sharpe"]),
        "nostra_maximum_drawdown": quantile_summary(distributions["maximum_drawdown"]),
        "nostra_final_equity": quantile_summary(distributions["final_equity"]),
        "outperformance_frequency_vs_bitcoin": float(
            np.mean([record["outperforms_bitcoin"] for record in central_records])
        ),
        "outperformance_frequency_vs_exposure_matched": float(
            np.mean([record["outperforms_matched"] for record in central_records])
        ),
        "publication_boundary": (
            "Seuls des agrégats de distribution sont publiés; les résultats "
            "par date de départ ne sont pas exportés."
        ),
    }
    return summary, distributions


def rolling_horizon_analysis(
    data: pd.DataFrame,
    exposure_matched_level: float,
) -> list[dict[str, Any]]:
    raw = data["raw_bitcoin_return"].to_numpy(dtype=float)
    exposure = data["applied_exposure"].to_numpy(dtype=float)
    records: list[dict[str, Any]] = []

    for horizon in ROLLING_HORIZONS:
        nostra_returns_distribution: list[float] = []
        nostra_drawdown_distribution: list[float] = []
        positive: list[int] = []
        outperform_bitcoin: list[int] = []
        outperform_matched: list[int] = []

        for start in range(0, len(data) - horizon + 1):
            end = start + horizon
            nostra_returns, _ = strategy_returns_from_cash(raw[start:end], exposure[start:end])
            bitcoin_returns = constant_exposure_returns(raw[start:end], 1.0)
            matched_returns = constant_exposure_returns(raw[start:end], exposure_matched_level)

            nostra_final = float(equity_from_returns(nostra_returns)[-1])
            bitcoin_final = float(equity_from_returns(bitcoin_returns)[-1])
            matched_final = float(equity_from_returns(matched_returns)[-1])

            nostra_returns_distribution.append(nostra_final - 1.0)
            nostra_drawdown_distribution.append(maximum_drawdown(nostra_returns))
            positive.append(int(nostra_final > 1.0))
            outperform_bitcoin.append(int(nostra_final > bitcoin_final))
            outperform_matched.append(int(nostra_final > matched_final))

        records.append(
            {
                "horizon_observations": horizon,
                "window_count": len(nostra_returns_distribution),
                "overlapping_windows": True,
                "nostra_total_return": quantile_summary(nostra_returns_distribution),
                "nostra_maximum_drawdown": quantile_summary(nostra_drawdown_distribution),
                "positive_window_frequency": float(np.mean(positive)),
                "outperformance_frequency_vs_bitcoin": float(np.mean(outperform_bitcoin)),
                "outperformance_frequency_vs_exposure_matched": float(np.mean(outperform_matched)),
            }
        )

    return records


def format_percent(value: float, decimals: int = 2) -> str:
    return f"{value * 100:.{decimals}f} %".replace(".", ",")


def format_number(value: float, decimals: int = 3) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def load_plotting() -> tuple[Any, Any]:
    """Charge Matplotlib uniquement lors de la génération graphique."""
    matplotlib = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    pyplot = importlib.import_module("matplotlib.pyplot")
    ticker = importlib.import_module("matplotlib.ticker")
    return pyplot, ticker.PercentFormatter


def plot_matched_comparators(records: list[dict[str, Any]]) -> None:
    plt, PercentFormatter = load_plotting()
    short_labels = ["Nostra", "Bitcoin", "Ajusté\nexposition", "Ajusté\nrisque"]
    colors = [NOSTRA_COLOR, BITCOIN_COLOR, MATCHED_COLOR, RISK_MATCHED_COLOR]
    metrics_to_plot = [
        ("final_equity", "Capital final", False),
        ("cagr", "Taux de croissance annuel composé", True),
        ("annualized_volatility", "Volatilité annualisée", True),
        ("maximum_drawdown", "Perte maximale", True),
    ]

    figure, axes = plt.subplots(2, 2, figsize=(11.0, 8.0))
    for axis, (field, title, percent) in zip(axes.flat, metrics_to_plot, strict=True):
        values = [float(record[field]) for record in records]
        bars = axis.bar(short_labels, values, color=colors)
        axis.set_title(title, loc="left", fontweight="bold", fontsize=11)
        axis.grid(axis="y", color=GRID_COLOR, linewidth=0.6)
        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        if percent:
            axis.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
        for bar, value in zip(bars, values, strict=True):
            label = format_percent(value) if percent else format_number(value, 2)
            axis.annotate(
                label,
                (bar.get_x() + bar.get_width() / 2, value),
                xytext=(0, 4 if value >= 0 else -14),
                textcoords="offset points",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=7.5,
            )

    figure.suptitle(
        "Comparaison avec des expositions constantes ajustées",
        x=0.07,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )
    figure.text(
        0.07,
        0.015,
        "Comparateurs calculés avec la même série bitcoin, le même capital initial "
        "et le même coût d'entrée de 25 points de base.",
        fontsize=7.8,
        color="#626B72",
    )
    figure.tight_layout(rect=(0.03, 0.05, 0.99, 0.95))
    FIGURE_5_8.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURE_5_8, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def plot_concentration(records: list[dict[str, Any]]) -> None:
    plt, _ = load_plotting()
    selected = {
        strategy: [record for record in records if record["strategy"] == strategy]
        for strategy in ("Nostra AI V5.246", "Bitcoin passif")
    }

    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.8), sharey=False)
    for axis, strategy, color in zip(
        axes,
        ("Nostra AI V5.246", "Bitcoin passif"),
        (NOSTRA_COLOR, BITCOIN_COLOR),
        strict=True,
    ):
        strategy_records = sorted(selected[strategy], key=lambda item: item["count"])
        x = np.arange(len(strategy_records))
        width = 0.25
        axis.bar(
            x - width,
            [record["final_equity_without_top"] for record in strategy_records],
            width,
            label="Sans meilleurs jours",
            color=color,
        )
        axis.bar(
            x,
            [record["final_equity_without_bottom"] for record in strategy_records],
            width,
            label="Sans pires jours",
            color=MATCHED_COLOR,
        )
        axis.bar(
            x + width,
            [record["final_equity_without_top_and_bottom"] for record in strategy_records],
            width,
            label="Sans extrêmes symétriques",
            color="#B5BDC3",
        )
        axis.set_xticks(x)
        axis.set_xticklabels([str(record["count"]) for record in strategy_records])
        axis.set_xlabel("Nombre de journées neutralisées")
        axis.set_ylabel("Capital final recalculé")
        axis.set_title(strategy, loc="left", fontweight="bold", fontsize=11)
        axis.grid(axis="y", color=GRID_COLOR, linewidth=0.6)
        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    axes[0].legend(frameon=False, fontsize=8)
    figure.suptitle(
        "Concentration de la trajectoire dans les meilleures et pires journées",
        x=0.07,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    figure.text(
        0.07,
        0.015,
        "Les journées sont classées séparément pour chaque stratégie. "
        "La neutralisation fixe leur rendement à zéro.",
        fontsize=7.8,
        color="#626B72",
    )
    figure.tight_layout(rect=(0.03, 0.06, 0.99, 0.92))
    figure.savefig(FIGURE_5_9, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def plot_attribution(attribution: dict[str, Any]) -> None:
    plt, _ = load_plotting()
    exposure_records = attribution["exposure_buckets"]
    market_records = attribution["bitcoin_direction_groups"]

    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.8))

    axis = axes[0]
    labels = [str(record["bucket"]) for record in exposure_records]
    values = [float(record["log_return_contribution"]) for record in exposure_records]
    axis.barh(labels, values, color=NOSTRA_COLOR)
    axis.axvline(0.0, color=TEXT_COLOR, linewidth=0.8)
    axis.set_xlabel("Contribution au logarithme de richesse")
    axis.set_title("A. Contribution par niveau d'exposition", loc="left", fontweight="bold")
    axis.grid(axis="x", color=GRID_COLOR, linewidth=0.6)
    axis.set_axisbelow(True)

    axis = axes[1]
    x = np.arange(len(market_records))
    width = 0.36
    axis.bar(
        x - width / 2,
        [record["nostra_log_return_contribution"] for record in market_records],
        width,
        label="Nostra AI V5.246",
        color=NOSTRA_COLOR,
    )
    axis.bar(
        x + width / 2,
        [record["matched_comparator_log_return_contribution"] for record in market_records],
        width,
        label="Bitcoin ajusté à l'exposition",
        color=MATCHED_COLOR,
    )
    axis.axhline(0.0, color=TEXT_COLOR, linewidth=0.8)
    axis.set_xticks(x)
    axis.set_xticklabels(["Bitcoin en hausse", "Bitcoin en baisse"])
    axis.set_ylabel("Contribution au logarithme de richesse")
    axis.set_title("B. Contribution selon le signe du bitcoin", loc="left", fontweight="bold")
    axis.legend(frameon=False, fontsize=8)
    axis.grid(axis="y", color=GRID_COLOR, linewidth=0.6)
    axis.set_axisbelow(True)

    for axis in axes:
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    figure.suptitle(
        "Attribution économique agrégée",
        x=0.07,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    figure.text(
        0.07,
        0.015,
        "Les contributions utilisent les logarithmes de richesse, additifs sur "
        "l'ensemble de la période. Elles décrivent une décomposition historique "
        "et non une causalité structurelle.",
        fontsize=7.8,
        color="#626B72",
    )
    figure.tight_layout(rect=(0.03, 0.06, 0.99, 0.92))
    figure.savefig(FIGURE_5_10, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def plot_start_date_sensitivity(distributions: dict[str, list[float]]) -> None:
    plt, PercentFormatter = load_plotting()
    figure, axes = plt.subplots(1, 3, figsize=(11.0, 4.5))
    fields = [
        ("cagr", "Taux de croissance annuel composé", True),
        ("sharpe", "Ratio de Sharpe", False),
        ("maximum_drawdown", "Perte maximale", True),
    ]
    for axis, (field, title, percent) in zip(axes, fields, strict=True):
        values = np.asarray(distributions[field], dtype=float)
        axis.boxplot(
            values,
            vert=True,
            widths=0.45,
            showfliers=True,
            patch_artist=True,
            boxprops={"facecolor": NOSTRA_COLOR, "alpha": 0.85},
            medianprops={"color": "white", "linewidth": 1.5},
        )
        axis.set_xticks([])
        axis.set_title(title, fontsize=10, fontweight="bold")
        axis.grid(axis="y", color=GRID_COLOR, linewidth=0.6)
        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        if percent:
            axis.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))

    figure.suptitle(
        "Sensibilité aux dates de départ mensuelles",
        x=0.07,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    figure.text(
        0.07,
        0.015,
        "Chaque sous-période se termine le 2 juin 2026 et comporte au moins "
        "365 observations. Le capital est réinitialisé à 1 et le coût d'entrée "
        "est réappliqué.",
        fontsize=7.8,
        color="#626B72",
    )
    figure.tight_layout(rect=(0.03, 0.07, 0.99, 0.90))
    figure.savefig(FIGURE_7_7, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def plot_rolling_horizons(records: list[dict[str, Any]]) -> None:
    plt, PercentFormatter = load_plotting()
    horizons = [int(record["horizon_observations"]) for record in records]
    positive = [float(record["positive_window_frequency"]) for record in records]
    versus_bitcoin = [float(record["outperformance_frequency_vs_bitcoin"]) for record in records]
    versus_matched = [
        float(record["outperformance_frequency_vs_exposure_matched"]) for record in records
    ]
    median_return = [float(record["nostra_total_return"]["median"]) for record in records]
    median_drawdown = [float(record["nostra_maximum_drawdown"]["median"]) for record in records]

    figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.8))
    axis = axes[0]
    axis.plot(horizons, positive, marker="o", label="Fenêtres positives", color=NOSTRA_COLOR)
    axis.plot(
        horizons,
        versus_bitcoin,
        marker="o",
        label="Surperformance du bitcoin",
        color=BITCOIN_COLOR,
    )
    axis.plot(
        horizons,
        versus_matched,
        marker="o",
        label="Surperformance du comparateur ajusté",
        color=MATCHED_COLOR,
    )
    axis.set_xscale("log")
    axis.set_xticks(horizons)
    axis.set_xticklabels([str(value) for value in horizons])
    axis.set_ylim(0.0, 1.05)
    axis.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    axis.set_xlabel("Horizon en observations")
    axis.set_ylabel("Fréquence")
    axis.set_title("A. Fréquences de résultat", loc="left", fontweight="bold")
    axis.legend(frameon=False, fontsize=7.5)

    axis = axes[1]
    axis.plot(
        horizons,
        median_return,
        marker="o",
        label="Rendement médian",
        color=NOSTRA_COLOR,
    )
    axis.plot(
        horizons,
        median_drawdown,
        marker="o",
        label="Perte maximale médiane",
        color="#7D8992",
    )
    axis.set_xscale("log")
    axis.set_xticks(horizons)
    axis.set_xticklabels([str(value) for value in horizons])
    axis.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    axis.set_xlabel("Horizon en observations")
    axis.set_ylabel("Valeur médiane")
    axis.set_title("B. Rendement et risque médians", loc="left", fontweight="bold")
    axis.legend(frameon=False, fontsize=8)

    for axis in axes:
        axis.grid(color=GRID_COLOR, linewidth=0.6)
        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    figure.suptitle(
        "Robustesse sur horizons glissants",
        x=0.07,
        ha="left",
        fontsize=14,
        fontweight="bold",
    )
    figure.text(
        0.07,
        0.015,
        "Les fenêtres se chevauchent et ne constituent pas des observations "
        "statistiquement indépendantes. Le coût d'entrée est réappliqué à chaque fenêtre.",
        fontsize=7.8,
        color="#626B72",
    )
    figure.tight_layout(rect=(0.03, 0.06, 0.99, 0.92))
    figure.savefig(FIGURE_7_8, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def render_part_v_table(
    comparator_records: list[dict[str, Any]],
    concentration_records: list[dict[str, Any]],
    attribution: dict[str, Any],
) -> str:
    lines = [
        "# Extension finale de la Partie V",
        "",
        "## Comparateurs ajustés",
        "",
        (
            "| Stratégie | Exposition constante | Capital final | CAGR | "
            "Volatilité | Sharpe | Perte maximale |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for record in comparator_records:
        exposure = record["constant_exposure"]
        exposure_text = "N/A" if exposure is None else format_percent(float(exposure), 4)
        lines.append(
            "| {strategy} | {exposure} | {final} | {cagr} | {volatility} | "
            "{sharpe} | {drawdown} |".format(
                strategy=record["strategy"],
                exposure=exposure_text,
                final=format_number(float(record["final_equity"]), 4),
                cagr=format_percent(float(record["cagr"])),
                volatility=format_percent(float(record["annualized_volatility"])),
                sharpe=format_number(float(record["sharpe"]), 3),
                drawdown=format_percent(float(record["maximum_drawdown"])),
            )
        )

    lines.extend(
        [
            "",
            "## Concentration des rendements",
            "",
            (
                "| Stratégie | Jours | Capital sans meilleurs jours | "
                "Capital sans pires jours | Capital sans extrêmes symétriques |"
            ),
            "|---|---:|---:|---:|---:|",
        ]
    )
    for record in concentration_records:
        if record["strategy"] not in ("Nostra AI V5.246", "Bitcoin passif"):
            continue
        lines.append(
            "| {strategy} | {count} | {without_top} | {without_bottom} | {without_both} |".format(
                strategy=record["strategy"],
                count=record["count"],
                without_top=format_number(float(record["final_equity_without_top"]), 4),
                without_bottom=format_number(float(record["final_equity_without_bottom"]), 4),
                without_both=format_number(float(record["final_equity_without_top_and_bottom"]), 4),
            )
        )

    lines.extend(
        [
            "",
            "## Attribution par niveau d'exposition",
            "",
            (
                "| Tranche | Observations | Part de la période | "
                "Exposition moyenne | Contribution logarithmique | "
                "Part de la richesse logarithmique |"
            ),
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for record in attribution["exposure_buckets"]:
        lines.append(
            (
                "| {bucket} | {observations} | {share} | {average} | "
                "{log_contribution} | {log_share} |"
            ).format(
                bucket=record["bucket"],
                observations=record["observations"],
                share=format_percent(float(record["observation_share"])),
                average=format_percent(float(record["average_exposure"])),
                log_contribution=format_number(float(record["log_return_contribution"]), 4),
                log_share=format_percent(float(record["share_of_total_log_return"])),
            )
        )

    lines.extend(
        [
            "",
            "Les contributions sont descriptives et ne constituent pas une attribution causale.",
            "",
        ]
    )
    return "\n".join(lines)


def render_part_vii_table(
    start_summary: dict[str, Any],
    rolling_records: list[dict[str, Any]],
) -> str:
    lines = [
        "# Extension finale de la Partie VII",
        "",
        "## Sensibilité aux dates de départ",
        "",
        "| Indicateur | Valeur |",
        "|---|---:|",
        (
            "| Dates mensuelles retenues | "
            f"{start_summary['monthly_start_count_with_at_least_365_observations']} |"
        ),
        (
            "| Fréquence de surperformance du bitcoin | "
            f"{format_percent(float(start_summary['outperformance_frequency_vs_bitcoin']))} |"
        ),
        (
            "| Fréquence de surperformance du comparateur ajusté | "
            f"{format_percent(float(start_summary['outperformance_frequency_vs_exposure_matched']))} |"  # noqa: E501
        ),
        f"| CAGR minimal | {format_percent(float(start_summary['nostra_cagr']['minimum']))} |",
        f"| CAGR médian | {format_percent(float(start_summary['nostra_cagr']['median']))} |",
        f"| CAGR maximal | {format_percent(float(start_summary['nostra_cagr']['maximum']))} |",
        (
            "| Perte maximale médiane | "
            f"{format_percent(float(start_summary['nostra_maximum_drawdown']['median']))} |"
        ),
        "",
        "## Horizons glissants",
        "",
        (
            "| Horizon | Fenêtres | Positives | Surperformance bitcoin | "
            "Surperformance ajustée | Rendement médian | "
            "Perte maximale médiane |"
        ),
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in rolling_records:
        lines.append(
            (
                "| {horizon} | {count} | {positive} | {bitcoin} | "
                "{matched} | {median_return} | {median_drawdown} |"
            ).format(
                horizon=record["horizon_observations"],
                count=record["window_count"],
                positive=format_percent(float(record["positive_window_frequency"])),
                bitcoin=format_percent(float(record["outperformance_frequency_vs_bitcoin"])),
                matched=format_percent(
                    float(record["outperformance_frequency_vs_exposure_matched"])
                ),
                median_return=format_percent(float(record["nostra_total_return"]["median"])),
                median_drawdown=format_percent(float(record["nostra_maximum_drawdown"]["median"])),
            )
        )
    lines.extend(
        [
            "",
            "Les fenêtres se chevauchent et ne constituent pas des observations indépendantes.",
            "",
        ]
    )
    return "\n".join(lines)


def write_manifest(
    directory: Path,
    package: str,
    paths: list[Path],
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(paths, key=lambda item: str(item.relative_to(ROOT))):
        require(path.is_file(), f"Fichier attendu absent : {path}")
        records.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": 1,
        "package": package,
        "model": "Nostra AI V5.246",
        "source_release": "v0.3.0",
        "files": records,
    }
    write_json(directory / "manifest.json", manifest)
    checksums = "\n".join(f"{record['sha256']}  {record['path']}" for record in records)
    (directory / "SHA256SUMS").write_text(checksums + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    data, reconciliation = load_data(args.private_input)

    comparator_records, series = matched_comparators(data)
    concentration_records = concentration_analysis(series)
    attribution = attribution_analysis(data, series)

    exposure_matched_level = next(
        float(record["constant_exposure"])
        for record in comparator_records
        if record["strategy"] == "Bitcoin ajusté à l'exposition"
    )
    start_summary, start_distributions = start_date_sensitivity(data, exposure_matched_level)
    rolling_records = rolling_horizon_analysis(data, exposure_matched_level)

    part_v_payload = {
        "schema_version": 1,
        "analysis": "part_v_final_quantitative_extension",
        "model": "Nostra AI V5.246",
        "release": "v0.3.0",
        "period": {
            "start": EXPECTED_START.isoformat(),
            "end": EXPECTED_END.isoformat(),
            "observations": EXPECTED_OBSERVATIONS,
        },
        "reconciliation": reconciliation,
        "comparators": comparator_records,
        "concentration": concentration_records,
        "attribution": attribution,
        "publication_boundary": (
            "Aucune date quotidienne, exposition quotidienne ou série quotidienne "
            "Nostra n'est exportée."
        ),
    }
    part_vii_payload = {
        "schema_version": 1,
        "analysis": "part_vii_entry_date_and_rolling_horizon_extension",
        "model": "Nostra AI V5.246",
        "release": "v0.3.0",
        "period": {
            "start": EXPECTED_START.isoformat(),
            "end": EXPECTED_END.isoformat(),
            "observations": EXPECTED_OBSERVATIONS,
        },
        "reconciliation": reconciliation,
        "start_date_sensitivity": start_summary,
        "rolling_horizons": rolling_records,
        "publication_boundary": (
            "Les résultats par date de départ et par fenêtre individuelle ne sont "
            "pas exportés; seuls les agrégats de distribution sont publiés."
        ),
    }

    write_json(PART_V_SUMMARY, part_v_payload)
    write_json(PART_VII_SUMMARY, part_vii_payload)
    PART_V_TABLE.parent.mkdir(parents=True, exist_ok=True)
    PART_V_TABLE.write_text(
        render_part_v_table(
            comparator_records,
            concentration_records,
            attribution,
        ),
        encoding="utf-8",
    )
    PART_VII_TABLE.write_text(
        render_part_vii_table(start_summary, rolling_records),
        encoding="utf-8",
    )

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plot_matched_comparators(comparator_records)
    plot_concentration(concentration_records)
    plot_attribution(attribution)
    plot_start_date_sensitivity(start_distributions)
    plot_rolling_horizons(rolling_records)

    write_manifest(
        PART_V_DIR,
        "part_v_final_quantitative_extension",
        [
            PART_V_SUMMARY,
            PART_V_TABLE,
            FIGURE_5_8,
            FIGURE_5_9,
            FIGURE_5_10,
            GENERATOR_PATH,
        ],
    )
    write_manifest(
        PART_VII_DIR,
        "part_vii_entry_date_and_rolling_horizon_extension",
        [
            PART_VII_SUMMARY,
            PART_VII_TABLE,
            FIGURE_7_7,
            FIGURE_7_8,
            GENERATOR_PATH,
        ],
    )

    print(f"Exposition ajustée : {exposure_matched_level:.12f}")
    risk_matched_level = next(
        float(record["constant_exposure"])
        for record in comparator_records
        if record["strategy"] == "Bitcoin ajusté au risque"
    )
    print(f"Exposition ajustée au risque : {risk_matched_level:.12f}")
    print(
        "Dates mensuelles centrales : "
        f"{start_summary['monthly_start_count_with_at_least_365_observations']}"
    )
    print(f"Horizons glissants : {len(rolling_records)}")
    print("PASS_FINAL_QUANTITATIVE_EXTENSIONS")


if __name__ == "__main__":
    main()
