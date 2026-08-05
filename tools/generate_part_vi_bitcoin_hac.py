#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from hilmarbench.temporal_statistics import hac_adjusted_sharpe

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = ROOT / "artifacts" / "releases" / "v0.2.1" / "baseline_daily_curves.csv"

OUTPUT_PATH = ROOT / "artifacts" / "report_support" / "part_vi" / "bitcoin_passive_hac_sharpe.json"

EXPECTED_SOURCE_SHA256 = "4cdd65f8b27c97c42ebc30fb7974024bf11af3cd1e5eea85e39b4c3fa7310d0d"

EXPECTED_OBSERVATIONS = 2211
EXPECTED_FINAL_EQUITY = 7.212950328296465

EXPECTED_START = pd.Timestamp("2020-05-14", tz="UTC")
EXPECTED_END = pd.Timestamp("2026-06-02", tz="UTC")

ANNUALIZATION = 365
HAC_LAGS = [5, 7, 10, 21, 30, 60]


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


def load_returns() -> tuple[pd.DataFrame, np.ndarray]:
    require(
        SOURCE_PATH.is_file(),
        f"Source absente : {SOURCE_PATH.relative_to(ROOT)}",
    )

    observed_sha = sha256_file(SOURCE_PATH)

    require(
        observed_sha == EXPECTED_SOURCE_SHA256,
        f"Empreinte source non conforme : {observed_sha}",
    )

    frame = pd.read_csv(
        SOURCE_PATH,
        usecols=[
            "timestamp",
            "buy_and_hold_equity",
        ],
    )

    frame["timestamp"] = pd.to_datetime(
        frame["timestamp"],
        utc=True,
        errors="raise",
    )

    frame["buy_and_hold_equity"] = pd.to_numeric(
        frame["buy_and_hold_equity"],
        errors="raise",
    )

    frame = frame.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)

    require(
        len(frame) == EXPECTED_OBSERVATIONS,
        (f"{EXPECTED_OBSERVATIONS} observations attendues, {len(frame)} obtenues."),
    )

    require(
        frame["timestamp"].iloc[0] == EXPECTED_START,
        "Date initiale non conforme.",
    )

    require(
        frame["timestamp"].iloc[-1] == EXPECTED_END,
        "Date finale non conforme.",
    )

    final_equity = float(frame["buy_and_hold_equity"].iloc[-1])

    require(
        abs(final_equity - EXPECTED_FINAL_EQUITY) < 1e-12,
        f"Capital final non réconcilié : {final_equity:.15f}",
    )

    returns = frame["buy_and_hold_equity"].pct_change()

    # Convention publique existante :
    # le capital antérieur à la première observation vaut 1.
    returns.iloc[0] = float(frame["buy_and_hold_equity"].iloc[0]) - 1.0

    values = returns.to_numpy(dtype=float)

    require(
        bool(np.isfinite(values).all()),
        "La série de rendements contient une valeur invalide.",
    )

    return frame, values


def build_payload() -> dict[str, object]:
    frame, returns = load_returns()

    records = [
        asdict(
            hac_adjusted_sharpe(
                returns,
                lag_count=lag,
                annualization=ANNUALIZATION,
            )
        )
        for lag in HAC_LAGS
    ]

    canonical = next(record for record in records if record["lag_count"] == 21)

    require(
        abs(canonical["conventional_annualized_sharpe"] - 0.8535246890964329) < 1e-14,
        "Sharpe conventionnel non conforme.",
    )

    require(
        abs(canonical["hac_adjusted_annualized_sharpe"] - 0.8183668937097701) < 1e-14,
        "Sharpe HAC à 21 retards non conforme.",
    )

    return {
        "schema_version": 1,
        "analysis": "bitcoin_passive_hac_sharpe",
        "method": ("Newey-West long-run variance with Bartlett kernel"),
        "source": {
            "path": SOURCE_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(SOURCE_PATH),
            "equity_column": "buy_and_hold_equity",
            "verification_level": "public-curve-verified",
        },
        "period": {
            "start": frame["timestamp"].iloc[0].strftime("%Y-%m-%d"),
            "end": frame["timestamp"].iloc[-1].strftime("%Y-%m-%d"),
            "observations": len(frame),
            "annualization": ANNUALIZATION,
        },
        "reconciliation": {
            "final_equity": float(frame["buy_and_hold_equity"].iloc[-1]),
        },
        "canonical": canonical,
        "sensitivity_records": records,
        "limitations": [
            (
                "The calculation is retrospective and derived "
                "from the frozen public daily bitcoin curve."
            ),
            (
                "The difference between two HAC-adjusted Sharpe "
                "ratios is descriptive and is not itself a formal "
                "test of equality."
            ),
        ],
    }


def main() -> None:
    payload = build_payload()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    canonical = payload["canonical"]

    print("PASS_BITCOIN_HAC_REPORT_SUPPORT")
    print(OUTPUT_PATH.relative_to(ROOT))
    print(f"Sharpe conventionnel : {canonical['conventional_annualized_sharpe']:.10f}")
    print(f"Sharpe HAC 21 : {canonical['hac_adjusted_annualized_sharpe']:.10f}")


if __name__ == "__main__":
    main()
