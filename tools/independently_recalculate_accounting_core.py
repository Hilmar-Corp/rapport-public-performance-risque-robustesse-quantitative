#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CURVES = ROOT / "artifacts" / "releases" / "v0.2.1" / "baseline_daily_curves.csv"
EXECUTION_EXPORT = (
    ROOT
    / "artifacts"
    / "candidates"
    / "v0.3.0"
    / "quantitative_aggregates"
    / "execution_cost_delay.json"
)
SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_x"
SUMMARY_PATH = SUPPORT_DIR / "independent_accounting_recalculation_summary.json"
TABLE_PATH = ROOT / "docs" / "tables" / "part_x_independent_recalculation_results.md"
SCRIPT_PATH = ROOT / "tools" / "independently_recalculate_accounting_core.py"

EXPECTED_PRIVATE_SHA256 = "056e13af2b26b0e449e502bf814db1a6a396f90aa4cb2bae74b2771ce8285c2e"
EXPECTED_PUBLIC_SHA256 = "4cdd65f8b27c97c42ebc30fb7974024bf11af3cd1e5eea85e39b4c3fa7310d0d"
EXPECTED_EXECUTION_SHA256 = "ae0485d907b9c3cb01fb26dbe05f95bbdc127491b31a458bfdb051fbc04ae38c"
EXPECTED_OBSERVATIONS = 2211
EXPECTED_START = pd.Timestamp("2020-05-14", tz="UTC")
EXPECTED_END = pd.Timestamp("2026-06-02", tz="UTC")
ANNUALIZATION = 365.0
CENTRAL_COST_BPS = 25.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recalcule indépendamment le noyau comptable de Nostra AI V5.246."
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


def returns_from_equity(equity: np.ndarray) -> np.ndarray:
    require(len(equity) > 1, "Deux valeurs de capital au minimum sont requises.")
    require(np.all(equity > 0.0), "Le capital doit rester strictement positif.")
    returns = np.empty_like(equity, dtype=float)
    returns[0] = equity[0] - 1.0
    returns[1:] = equity[1:] / equity[:-1] - 1.0
    return returns


def independently_backtest(
    asset_returns: np.ndarray,
    applied_exposure: np.ndarray,
    cost_bps: float,
    extra_delay: int,
) -> dict[str, np.ndarray | float]:
    require(extra_delay >= 0, "Le délai supplémentaire ne peut pas être négatif.")
    require(len(asset_returns) == len(applied_exposure), "Longueurs incompatibles.")
    if extra_delay == 0:
        delayed = applied_exposure.copy()
    else:
        delayed = np.concatenate(
            (np.zeros(extra_delay, dtype=float), applied_exposure[:-extra_delay])
        )
    previous = np.concatenate((np.array([0.0]), delayed[:-1]))
    turnover = np.abs(delayed - previous)
    net_returns = delayed * asset_returns - (cost_bps / 10_000.0) * turnover
    require(np.all(net_returns > -1.0), "Un rendement net atteint -100 %.")
    equity = np.cumprod(1.0 + net_returns)
    return {
        "exposure": delayed,
        "turnover": turnover,
        "net_returns": net_returns,
        "equity": equity,
        "turnover_total": float(np.sum(turnover)),
    }


def independently_measure(net_returns: np.ndarray) -> dict[str, float]:
    equity = np.cumprod(1.0 + net_returns)
    previous_peak = np.maximum.accumulate(np.concatenate((np.array([1.0]), equity)))[1:]
    drawdown = equity / previous_peak - 1.0
    volatility_daily = float(np.std(net_returns, ddof=1))
    final_equity = float(equity[-1])
    return {
        "final_equity": final_equity,
        "cagr": final_equity ** (ANNUALIZATION / len(net_returns)) - 1.0,
        "annualized_volatility": volatility_daily * math.sqrt(ANNUALIZATION),
        "sharpe": (float(np.mean(net_returns)) / volatility_daily * math.sqrt(ANNUALIZATION)),
        "maximum_drawdown": float(np.min(drawdown)),
    }


def resolve_applied_exposure(
    raw_position: np.ndarray,
    asset_returns: np.ndarray,
    official_returns: np.ndarray,
) -> tuple[np.ndarray, str, float]:
    candidates = {
        "as_provided": raw_position,
        "one_observation_shift": np.concatenate((np.array([0.0]), raw_position[:-1])),
    }
    results: list[tuple[float, str, np.ndarray]] = []
    for name, exposure in candidates.items():
        backtest = independently_backtest(
            asset_returns,
            exposure,
            CENTRAL_COST_BPS,
            0,
        )
        difference = float(
            np.max(np.abs(np.asarray(backtest["net_returns"], dtype=float) - official_returns))
        )
        results.append((difference, name, exposure))
    results.sort(key=lambda item: item[0])
    best_difference, best_name, best_exposure = results[0]
    require(best_difference <= 1e-10, "Aucun alignement ne réconcilie Nostra.")
    require(results[1][0] > 1e-8, "Alignement de position ambigu.")
    return best_exposure.astype(float), best_name, best_difference


def load_inputs(private_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    private_path = private_path.expanduser().resolve()
    require(private_path.is_file(), f"Source privée absente : {private_path}")
    require(
        sha256_file(private_path) == EXPECTED_PRIVATE_SHA256,
        "Empreinte privée non conforme.",
    )
    require(
        sha256_file(PUBLIC_CURVES) == EXPECTED_PUBLIC_SHA256,
        "Empreinte publique non conforme.",
    )
    require(
        sha256_file(EXECUTION_EXPORT) == EXPECTED_EXECUTION_SHA256,
        "Empreinte de l'export coûts-délais non conforme.",
    )

    private = pd.read_csv(private_path)
    private = private[["timestamp", "v5246_equity_25bps", "v5246_position"]].copy()
    private["timestamp"] = pd.to_datetime(
        private["timestamp"], utc=True, errors="raise"
    ).dt.normalize()

    public = pd.read_csv(PUBLIC_CURVES)
    public = public[["timestamp", "buy_and_hold_equity"]].copy()
    public["timestamp"] = pd.to_datetime(
        public["timestamp"], utc=True, errors="raise"
    ).dt.normalize()

    data = public.merge(private, on="timestamp", validate="one_to_one")
    data = data.sort_values("timestamp").reset_index(drop=True)
    require(len(data) == EXPECTED_OBSERVATIONS, "Nombre d'observations non conforme.")
    require(data["timestamp"].iloc[0] == EXPECTED_START, "Date initiale non conforme.")
    require(data["timestamp"].iloc[-1] == EXPECTED_END, "Date finale non conforme.")

    bitcoin_equity = data["buy_and_hold_equity"].to_numpy(dtype=float)
    bitcoin_net_returns = returns_from_equity(bitcoin_equity)
    asset_returns = bitcoin_net_returns.copy()
    asset_returns[0] += CENTRAL_COST_BPS / 10_000.0

    nostra_equity = data["v5246_equity_25bps"].to_numpy(dtype=float)
    official_returns = returns_from_equity(nostra_equity)
    position = data["v5246_position"].to_numpy(dtype=float)
    exposure, alignment, difference = resolve_applied_exposure(
        position,
        asset_returns,
        official_returns,
    )

    data["asset_return"] = asset_returns
    data["applied_exposure"] = exposure
    data["official_nostra_return"] = official_returns
    return data, {
        "private_sha256": sha256_file(private_path),
        "public_sha256": sha256_file(PUBLIC_CURVES),
        "execution_export_sha256": sha256_file(EXECUTION_EXPORT),
        "position_alignment": alignment,
        "official_return_maximum_absolute_difference": difference,
    }


def reference_records() -> dict[tuple[float, int], dict[str, Any]]:
    payload = json.loads(EXECUTION_EXPORT.read_text(encoding="utf-8"))
    records = payload["data"]["records"]
    selected = {
        (float(record["cost_bps"]), int(record["delay_days"])): record
        for record in records
        if record["candidate"] == "artifact_verified_reference"
    }
    require(len(selected) == 18, "Dix-huit scénarios de référence sont attendus.")
    return selected


def render_table(records: list[dict[str, Any]]) -> str:
    lines = [
        "# Recalcul indépendant du noyau comptable",
        "",
        (
            "| Coût | Délai | Capital recalculé | Capital publié | Écart | "
            "CAGR recalculé | Sharpe recalculé | "
            "Perte maximale recalculée |"
        ),
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in records:
        lines.append(
            "| {cost:.0f} pb | {delay} | {calculated:.8f} | {published:.8f} | "
            "{difference:.2e} | {cagr:.6%} | {sharpe:.6f} | {drawdown:.6%} |".format(
                cost=record["cost_bps"],
                delay=record["delay_days"],
                calculated=record["calculated"]["final_equity"],
                published=record["published"]["final_equity"],
                difference=record["absolute_differences"]["final_equity"],
                cagr=record["calculated"]["cagr"],
                sharpe=record["calculated"]["sharpe"],
                drawdown=record["calculated"]["maximum_drawdown"],
            )
        )
    lines.extend(
        [
            "",
            "Le recalcul n'importe aucune fonction de `src/hilmarbench`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_manifest(paths: list[Path]) -> None:
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(paths, key=lambda item: str(item.relative_to(ROOT))):
        require(path.is_file(), f"Fichier absent : {path}")
        records.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    write_json(
        SUPPORT_DIR / "manifest.json",
        {
            "schema_version": 1,
            "package": "part_x_independent_accounting_recalculation",
            "model": "Nostra AI V5.246",
            "source_release": "v0.3.0",
            "files": records,
        },
    )
    (SUPPORT_DIR / "SHA256SUMS").write_text(
        "\n".join(f"{record['sha256']}  {record['path']}" for record in records) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    data, reconciliation = load_inputs(args.private_input)
    asset_returns = data["asset_return"].to_numpy(dtype=float)
    exposure = data["applied_exposure"].to_numpy(dtype=float)
    official_equity = data["v5246_equity_25bps"].to_numpy(dtype=float)
    references = reference_records()

    records: list[dict[str, Any]] = []
    maximum_differences = {
        "final_equity": 0.0,
        "cagr": 0.0,
        "annualized_volatility": 0.0,
        "sharpe": 0.0,
        "maximum_drawdown": 0.0,
        "turnover_total": 0.0,
    }

    for cost_bps in (0.0, 25.0, 100.0):
        for delay_days in (0, 1, 2):
            backtest = independently_backtest(
                asset_returns,
                exposure,
                cost_bps,
                delay_days,
            )
            measured = independently_measure(np.asarray(backtest["net_returns"], dtype=float))
            calculated = {
                **measured,
                "turnover_total": float(backtest["turnover_total"]),
            }
            reference = references[(cost_bps, delay_days)]
            published = {field: float(reference[field]) for field in maximum_differences}
            differences = {
                field: abs(calculated[field] - published[field]) for field in maximum_differences
            }
            for field, difference in differences.items():
                maximum_differences[field] = max(maximum_differences[field], difference)
            records.append(
                {
                    "cost_bps": cost_bps,
                    "delay_days": delay_days,
                    "calculated": calculated,
                    "published": published,
                    "absolute_differences": differences,
                }
            )

    official_backtest = independently_backtest(
        asset_returns,
        exposure,
        CENTRAL_COST_BPS,
        0,
    )
    official_equity_difference = float(
        np.max(np.abs(np.asarray(official_backtest["equity"], dtype=float) - official_equity))
    )
    require(
        official_equity_difference <= 1e-10,
        "La courbe officielle n'est pas réconciliée par la seconde implémentation.",
    )
    require(
        maximum_differences["final_equity"] <= 5e-8,
        "Écart excessif sur le capital final.",
    )
    require(maximum_differences["cagr"] <= 5e-8, "Écart excessif sur le CAGR.")
    require(
        maximum_differences["annualized_volatility"] <= 5e-8,
        "Écart excessif sur la volatilité.",
    )
    require(maximum_differences["sharpe"] <= 5e-8, "Écart excessif sur le Sharpe.")
    require(
        maximum_differences["maximum_drawdown"] <= 5e-8,
        "Écart excessif sur la perte maximale.",
    )
    require(
        maximum_differences["turnover_total"] <= 5e-8,
        "Écart excessif sur la rotation.",
    )

    payload = {
        "schema_version": 1,
        "analysis": "independent_accounting_core_recalculation",
        "model": "Nostra AI V5.246",
        "release": "v0.3.0",
        "implementation_boundary": (
            "Implémentation autonome ne dépendant d'aucune fonction de src/hilmarbench."
        ),
        "reconciliation": {
            **reconciliation,
            "official_equity_maximum_absolute_difference": official_equity_difference,
            "maximum_aggregate_absolute_differences": maximum_differences,
        },
        "scenario_records": records,
    }
    write_json(SUMMARY_PATH, payload)
    TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TABLE_PATH.write_text(render_table(records), encoding="utf-8")
    write_manifest([SUMMARY_PATH, TABLE_PATH, SCRIPT_PATH])

    print(f"Écart maximal courbe officielle : {official_equity_difference:.3e}")
    for field, difference in maximum_differences.items():
        print(f"Écart maximal {field} : {difference:.3e}")
    print("PASS_INDEPENDENT_ACCOUNTING_RECALCULATION")


if __name__ == "__main__":
    main()
