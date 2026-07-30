from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

RELEASE_FILES = {
    "SHA256SUMS",
    "baseline_daily_curves.csv",
    "benchmark_metrics.csv",
    "manifest.json",
    "methodology.json",
    "nostra_artifact_commitment.json",
}

SITE_FILES = {
    "SHA256SUMS",
    "manifest.json",
    "site_chart_daily_delayed.json",
    "site_chart_policy.json",
}

METRIC_INPUT_COLUMNS = [
    "strategy",
    "cost_bps",
    "date_start",
    "date_end",
    "observations",
    "final_equity",
    "total_return",
    "cagr",
    "annualized_volatility",
    "sharpe",
    "maximum_drawdown",
    "calmar",
]

METRIC_OUTPUT_COLUMNS = [
    "strategy",
    "verification_level",
    "cost_bps",
    "date_start",
    "date_end",
    "observations",
    "final_equity",
    "total_return",
    "cagr",
    "annualized_volatility",
    "sharpe",
    "maximum_drawdown",
    "calmar",
]

FORBIDDEN_PUBLIC_FIELDS = (
    "position",
    "probability",
    "prediction",
    "feature",
    "turnover",
    "transaction_cost",
    "gross_return",
    "net_return",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def normalize_name(value: str) -> str:
    return re.sub(
        r"[^A-Z0-9]+",
        "_",
        value.upper(),
    ).strip("_")


def is_nostra(value: str) -> bool:
    return normalize_name(value) in {
        "NOSTRA",
        "NOSTRA_AI",
    }


def load_private_hash(
    source_manifest: Path,
) -> str:
    data = json.loads(source_manifest.read_text(encoding="utf-8"))

    value = data["sources"]["production_trace"]["sha256"]

    if not isinstance(value, str) or not re.fullmatch(
        r"[a-f0-9]{64}",
        value,
    ):
        raise ValueError("Invalid private artifact SHA-256.")

    return value


def timestamp_column(
    frame: pd.DataFrame,
) -> str:
    candidates = [
        column
        for column in frame.columns
        if column.lower()
        in {
            "date",
            "datetime",
            "timestamp",
        }
    ]

    if len(candidates) != 1:
        raise ValueError("Exactly one timestamp column is required.")

    return candidates[0]


def write_integrity_files(
    root: Path,
) -> None:
    manifest_path = root / "manifest.json"
    sums_path = root / "SHA256SUMS"

    payload_files = sorted(
        path
        for path in root.iterdir()
        if (
            path.is_file()
            and path.name
            not in {
                "manifest.json",
                "SHA256SUMS",
            }
        )
    )

    manifest = {
        "schema_version": 1,
        "files": [
            {
                "path": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in payload_files
        ],
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    checksum_files = sorted(
        path for path in root.iterdir() if (path.is_file() and path.name != "SHA256SUMS")
    )

    sums_path.write_text(
        "".join(f"{sha256_file(path)}  {path.name}\n" for path in checksum_files),
        encoding="utf-8",
    )


def verify_manifest(
    root: Path,
) -> list[str]:
    issues: list[str] = []
    manifest_path = root / "manifest.json"

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (
        OSError,
        json.JSONDecodeError,
    ) as error:
        return [f"manifest unreadable: {error}"]

    entries = manifest.get("files")

    if not isinstance(entries, list):
        return ["manifest files must be a list"]

    expected_paths: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            issues.append("invalid manifest entry")
            continue

        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")

        if not isinstance(relative, str):
            issues.append("manifest entry path missing")
            continue

        expected_paths.add(relative)
        path = root / relative

        if not path.is_file():
            issues.append(f"{relative}: missing file")
            continue

        if path.stat().st_size != expected_size:
            issues.append(f"{relative}: size mismatch")

        if sha256_file(path) != expected_hash:
            issues.append(f"{relative}: SHA-256 mismatch")

    actual_paths = {
        path.name
        for path in root.iterdir()
        if (
            path.is_file()
            and path.name
            not in {
                "manifest.json",
                "SHA256SUMS",
            }
        )
    }

    for name in sorted(expected_paths - actual_paths):
        issues.append(f"{name}: listed but absent")

    for name in sorted(actual_paths - expected_paths):
        issues.append(f"{name}: unlisted file")

    return sorted(set(issues))


def build_release(
    metrics_path: Path,
    daily_path: Path,
    source_manifest: Path,
    output: Path,
) -> None:
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")

    private_hash = load_private_hash(source_manifest)

    metrics = pd.read_csv(metrics_path)
    daily = pd.read_csv(daily_path)

    missing = set(METRIC_INPUT_COLUMNS) - set(metrics.columns)

    if missing:
        raise ValueError("Missing metric columns: " + ", ".join(sorted(missing)))

    released_metrics = metrics[METRIC_INPUT_COLUMNS].copy()

    released_metrics["observations"] = pd.to_numeric(
        released_metrics["observations"],
        errors="raise",
    )

    released_metrics["final_equity"] = pd.to_numeric(
        released_metrics["final_equity"],
        errors="raise",
    )

    released_metrics["maximum_drawdown"] = pd.to_numeric(
        released_metrics["maximum_drawdown"],
        errors="raise",
    )

    if (released_metrics["observations"] <= 0).any():
        raise ValueError("Observations must be positive.")

    if (released_metrics["final_equity"] <= 0).any():
        raise ValueError("Final equity must be positive.")

    released_metrics["total_return"] = released_metrics["final_equity"] - 1.0

    released_metrics["cagr"] = [
        float(final_equity) ** (365.0 / float(observations)) - 1.0
        for final_equity, observations in zip(
            released_metrics["final_equity"],
            released_metrics["observations"],
            strict=True,
        )
    ]

    released_metrics["calmar"] = [
        (float(cagr) / abs(float(drawdown)) if float(drawdown) != 0.0 else float("nan"))
        for cagr, drawdown in zip(
            released_metrics["cagr"],
            released_metrics["maximum_drawdown"],
            strict=True,
        )
    ]

    released_metrics.insert(
        1,
        "verification_level",
        [
            ("artifact-verified" if is_nostra(strategy) else "code-reproducible")
            for strategy in released_metrics["strategy"].astype(str)
        ],
    )

    released_metrics = released_metrics[METRIC_OUTPUT_COLUMNS]

    ts_column = timestamp_column(daily)

    public_curve_columns = [ts_column]

    for column in daily.columns:
        lowered = column.lower()

        if column == ts_column:
            continue

        if lowered.startswith("nostra"):
            continue

        if not lowered.endswith(
            (
                "_equity",
                "_drawdown",
            )
        ):
            continue

        if any(fragment in lowered for fragment in FORBIDDEN_PUBLIC_FIELDS):
            continue

        public_curve_columns.append(column)

    if len(public_curve_columns) < 3:
        raise ValueError("Insufficient public baseline curves.")

    public_curves = daily[public_curve_columns].copy()

    for column in public_curves.columns:
        if column.lower().startswith("nostra"):
            raise ValueError("Nostra time series cannot enter the GitHub release.")

    output.mkdir(
        parents=True,
        exist_ok=False,
    )

    released_metrics.to_csv(
        output / "benchmark_metrics.csv",
        index=False,
    )

    public_curves.to_csv(
        output / "baseline_daily_curves.csv",
        index=False,
    )

    methodology = {
        "schema_version": 2,
        "evaluation": {
            "asset": "BTC",
            "frequency": "daily",
            "transaction_cost_bps": float(released_metrics["cost_bps"].iloc[0]),
            "initial_position": 0.0,
            "turnover_mode": "raw",
            "dynamic_signal_lag_days": 1,
            "annualization_factor": 365.0,
            "cagr_formula": ("final_equity ** (365 / observations) - 1"),
            "date_start": str(released_metrics["date_start"].iloc[0]),
            "date_end": str(released_metrics["date_end"].iloc[0]),
        },
        "public_baselines": {
            "status": "code-reproducible",
            "daily_curves_in_github": True,
        },
        "nostra": {
            "status": "artifact-verified",
            "model_code_in_github": False,
            "daily_equity_in_github": False,
            "daily_positions_public": False,
            "daily_returns_public": False,
            "turnover_public": False,
            "website_daily_equity": True,
            "website_minimum_delay_days": 14,
        },
        "publication_architecture": {
            "github": (
                "Evaluation code, public baseline "
                "curves, aggregate metrics and "
                "cryptographic commitment."
            ),
            "website": ("Delayed daily equity curves from a separately generated artifact."),
        },
        "limitations": [
            ("Nostra model logic, features, parameters and execution trace remain proprietary."),
            ("This release does not constitute independent external validation."),
        ],
    }

    (output / "methodology.json").write_text(
        json.dumps(
            methodology,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    commitment = {
        "schema_version": 1,
        "algorithm": "SHA-256",
        "private_evaluation_artifact_sha256": (private_hash),
        "disclosure": ("The committed evaluation artifact is retained privately."),
    }

    (output / "nostra_artifact_commitment.json").write_text(
        json.dumps(
            commitment,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    write_integrity_files(output)


def build_site_artifact(
    daily_path: Path,
    source_manifest: Path,
    output: Path,
    as_of_date: str,
    delay_days: int,
    decimals: int,
) -> None:
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")

    if delay_days < 14:
        raise ValueError("Delay cannot be shorter than 14 days.")

    private_hash = load_private_hash(source_manifest)

    daily = pd.read_csv(daily_path)
    ts_column = timestamp_column(daily)

    daily[ts_column] = pd.to_datetime(
        daily[ts_column],
        utc=True,
        errors="raise",
    )

    daily = daily.sort_values(ts_column).reset_index(drop=True)

    if daily[ts_column].duplicated().any():
        raise ValueError("Duplicate timestamps are forbidden.")

    equity_columns = [column for column in daily.columns if column.lower().endswith("_equity")]

    nostra_columns = [column for column in equity_columns if column.lower().startswith("nostra")]

    if len(nostra_columns) != 1:
        raise ValueError("Exactly one Nostra equity column is required.")

    if len(equity_columns) < 2:
        raise ValueError("At least one benchmark equity curve is required.")

    as_of = pd.Timestamp(as_of_date)

    as_of = as_of.tz_localize("UTC") if as_of.tzinfo is None else as_of.tz_convert("UTC")

    cutoff = as_of.normalize() - pd.Timedelta(days=delay_days)

    eligible = daily.loc[
        daily[ts_column] <= cutoff,
        [ts_column, *equity_columns],
    ].copy()

    if eligible.empty:
        raise ValueError("No observations satisfy the delay.")

    if eligible[equity_columns].isna().any().any():
        raise ValueError("Missing values in equity curves.")

    aliases: dict[str, str] = {}

    for column in equity_columns:
        if column == nostra_columns[0]:
            alias = "nostra"
        else:
            alias = re.sub(
                r"[^a-z0-9]+",
                "_",
                column.lower(),
            ).strip("_")

            if alias.endswith("_equity"):
                alias = alias[:-7]

        if alias in aliases.values():
            raise ValueError(f"Duplicate series alias: {alias}")

        aliases[column] = alias

    points: list[dict[str, Any]] = []

    for _, row in eligible.iterrows():
        point: dict[str, Any] = {"date": row[ts_column].strftime("%Y-%m-%d")}

        for column, alias in aliases.items():
            point[alias] = round(
                float(row[column]),
                decimals,
            )

        points.append(point)

    payload = {
        "schema_version": 1,
        "frequency": "daily",
        "as_of_date": as_of.strftime("%Y-%m-%d"),
        "publication_delay_days": (delay_days),
        "cutoff_date": cutoff.strftime("%Y-%m-%d"),
        "source_last_date": daily[ts_column].iloc[-1].strftime("%Y-%m-%d"),
        "last_published_date": eligible[ts_column].iloc[-1].strftime("%Y-%m-%d"),
        "rounding_decimals": decimals,
        "private_artifact_sha256": (private_hash),
        "series": sorted(aliases.values()),
        "points": points,
    }

    policy = {
        "schema_version": 1,
        "product_frequency": "daily",
        "chart_frequency": "daily",
        "minimum_publication_delay_days": 14,
        "contains_equity_curves": True,
        "contains_positions": False,
        "contains_daily_returns": False,
        "contains_turnover": False,
        "contains_transaction_costs": False,
        "contains_probabilities": False,
        "github_distribution": False,
        "destination": ("HilmarCorp website"),
    }

    output.mkdir(
        parents=True,
        exist_ok=False,
    )

    (output / "site_chart_daily_delayed.json").write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    (output / "site_chart_policy.json").write_text(
        json.dumps(
            policy,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    write_integrity_files(output)


def audit_release(root: Path) -> list[str]:
    issues: list[str] = []

    actual_files = {path.name for path in root.iterdir() if path.is_file()}

    for name in sorted(RELEASE_FILES - actual_files):
        issues.append(f"{name}: missing release file")

    for name in sorted(actual_files - RELEASE_FILES):
        issues.append(f"{name}: unexpected release file")

    metrics_path = root / "benchmark_metrics.csv"

    if metrics_path.is_file():
        metrics = pd.read_csv(metrics_path)

        if list(metrics.columns) != (METRIC_OUTPUT_COLUMNS):
            issues.append("benchmark_metrics.csv: invalid schema")

        normalized = metrics["strategy"].astype(str).map(normalize_name)

        nostra = metrics.loc[
            normalized.isin(
                {
                    "NOSTRA",
                    "NOSTRA_AI",
                }
            )
        ]

        if len(nostra) != 1:
            issues.append("benchmark_metrics.csv: invalid Nostra row count")
        elif nostra.iloc[0]["verification_level"] != "artifact-verified":
            issues.append("benchmark_metrics.csv: Nostra verification level invalid")

        baselines = metrics.loc[
            ~normalized.isin(
                {
                    "NOSTRA",
                    "NOSTRA_AI",
                }
            )
        ]

        if set(baselines["verification_level"]) != {"code-reproducible"}:
            issues.append("benchmark_metrics.csv: baseline verification invalid")

    curves_path = root / "baseline_daily_curves.csv"

    if curves_path.is_file():
        curves = pd.read_csv(
            curves_path,
            nrows=1,
        )

        for column in curves.columns:
            lowered = column.lower()

            if lowered.startswith("nostra"):
                issues.append(f"baseline_daily_curves.csv: Nostra column forbidden: {column}")

            if any(fragment in lowered for fragment in FORBIDDEN_PUBLIC_FIELDS):
                issues.append(f"baseline_daily_curves.csv: forbidden field: {column}")

    methodology_path = root / "methodology.json"

    if methodology_path.is_file():
        try:
            methodology = json.loads(methodology_path.read_text(encoding="utf-8"))

            nostra = methodology.get(
                "nostra",
                {},
            )

            expected_false = (
                "model_code_in_github",
                "daily_equity_in_github",
                "daily_positions_public",
                "daily_returns_public",
                "turnover_public",
            )

            for key in expected_false:
                if nostra.get(key) is not False:
                    issues.append(f"methodology.json: {key} must be false")

            if nostra.get("website_daily_equity") is not True:
                issues.append("methodology.json: website_daily_equity must be true")

            if nostra.get("website_minimum_delay_days") != 14:
                issues.append("methodology.json: website delay must equal 14")

        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            issues.append(f"methodology unreadable: {error}")

    issues.extend(verify_manifest(root))

    return sorted(set(issues))


def audit_site(root: Path) -> list[str]:
    issues: list[str] = []

    actual_files = {path.name for path in root.iterdir() if path.is_file()}

    for name in sorted(SITE_FILES - actual_files):
        issues.append(f"{name}: missing site file")

    for name in sorted(actual_files - SITE_FILES):
        issues.append(f"{name}: unexpected site file")

    chart_path = root / "site_chart_daily_delayed.json"

    if chart_path.is_file():
        try:
            chart = json.loads(chart_path.read_text(encoding="utf-8"))

            if chart.get("frequency") != "daily":
                issues.append("site chart frequency is not daily")

            delay = chart.get("publication_delay_days")

            if not isinstance(delay, int) or delay < 14:
                issues.append("site chart delay below 14 days")

            cutoff = pd.Timestamp(chart.get("cutoff_date"))

            points = chart.get("points")

            if not isinstance(points, list) or not points:
                issues.append("site chart has no points")
            else:
                dates: list[pd.Timestamp] = []

                for point in points:
                    if not isinstance(point, dict):
                        issues.append("invalid site point")
                        continue

                    if "nostra" not in point:
                        issues.append("Nostra curve missing")

                    for key in point:
                        lowered = key.lower()

                        if any(fragment in lowered for fragment in FORBIDDEN_PUBLIC_FIELDS):
                            issues.append(f"site chart contains forbidden field: {key}")

                    try:
                        point_date = pd.Timestamp(point["date"])
                        dates.append(point_date)

                        if point_date > cutoff:
                            issues.append("site point newer than cutoff")

                    except (
                        KeyError,
                        TypeError,
                        ValueError,
                    ):
                        issues.append("invalid site point date")

                if dates != sorted(set(dates)):
                    issues.append("site dates not unique and ordered")

            private_hash = chart.get("private_artifact_sha256")

            if not isinstance(
                private_hash,
                str,
            ) or not re.fullmatch(
                r"[a-f0-9]{64}",
                private_hash,
            ):
                issues.append("invalid site artifact hash")

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as error:
            issues.append(f"site chart unreadable: {error}")

    issues.extend(verify_manifest(root))

    return sorted(set(issues))


def print_audit(
    issues: list[str],
) -> None:
    if issues:
        print("FINAL PUBLICATION GATE FAILED")
        print()

        for issue in issues:
            print(f"- {issue}")

        raise SystemExit(1)

    print("FINAL PUBLICATION GATE PASSED")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    release = subparsers.add_parser("build-release")
    release.add_argument(
        "--metrics",
        type=Path,
        required=True,
    )
    release.add_argument(
        "--daily",
        type=Path,
        required=True,
    )
    release.add_argument(
        "--source-manifest",
        type=Path,
        required=True,
    )
    release.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    site = subparsers.add_parser("build-site")
    site.add_argument(
        "--daily",
        type=Path,
        required=True,
    )
    site.add_argument(
        "--source-manifest",
        type=Path,
        required=True,
    )
    site.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    site.add_argument(
        "--as-of-date",
        required=True,
    )
    site.add_argument(
        "--delay-days",
        type=int,
        default=14,
    )
    site.add_argument(
        "--decimals",
        type=int,
        default=6,
    )

    audit_release_parser = subparsers.add_parser("audit-release")
    audit_release_parser.add_argument(
        "--root",
        type=Path,
        required=True,
    )

    audit_site_parser = subparsers.add_parser("audit-site")
    audit_site_parser.add_argument(
        "--root",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "build-release":
        build_release(
            args.metrics,
            args.daily,
            args.source_manifest,
            args.output,
        )
        print("FINAL GITHUB RELEASE BUILT")
        print(args.output)
        return

    if args.command == "build-site":
        build_site_artifact(
            args.daily,
            args.source_manifest,
            args.output,
            args.as_of_date,
            args.delay_days,
            args.decimals,
        )
        print("FINAL SITE ARTIFACT BUILT")
        print(args.output)
        return

    if args.command == "audit-release":
        print_audit(audit_release(args.root))
        return

    if args.command == "audit-site":
        print_audit(audit_site(args.root))
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
