from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

TEXT_SUFFIXES = {
    "",
    ".cff",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
    ".sh",
}

IGNORED_DIRECTORIES = {
    ".git",
    ".hypothesis",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "htmlcov",
    "build",
    "dist",
}

IGNORED_FILE_NAMES = {
    ".coverage",
    "coverage.xml",
}

FORBIDDEN_SUFFIXES = {
    ".env",
    ".feather",
    ".joblib",
    ".key",
    ".npy",
    ".npz",
    ".onnx",
    ".parquet",
    ".pem",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
}

APPROVED_RELEASE_FILES = {
    "SHA256SUMS",
    "baseline_daily_curves.csv",
    "benchmark_metrics.csv",
    "manifest.json",
    "methodology.json",
    "nostra_artifact_commitment.json",
}

APPROVED_METRIC_COLUMNS = [
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

PRIVATE_COLUMN_FRAGMENTS = (
    "position",
    "probability",
    "prediction",
    "feature",
    "turnover",
    "transaction_cost",
    "gross_return",
    "net_return",
)


def _forbidden_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    github_token = "g" + "hp_"
    api_secret = "s" + "k-"
    aws_prefix = "AK" + "IA"
    private_key = "BEGIN " + "PRIVATE " + "KEY"

    return (
        (
            "absolute macOS user path",
            re.compile(
                r"/U(?:sers)/[^/\s]+/",
                re.IGNORECASE,
            ),
        ),
        (
            "private server path",
            re.compile(
                r"/o(?:pt)/h(?:ilmar)/",
                re.IGNORECASE,
            ),
        ),
        (
            "IPv4 address",
            re.compile(
                r"(?<![=A-Za-z0-9_.-])"
                r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
                r"(?![A-Za-z0-9_.-])"
            ),
        ),
        (
            "GitHub token",
            re.compile(
                rf"\b{re.escape(github_token)}"
                r"[A-Za-z0-9]{20,}\b"
            ),
        ),
        (
            "API secret",
            re.compile(
                rf"\b{re.escape(api_secret)}"
                r"[A-Za-z0-9_-]{20,}\b"
            ),
        ),
        (
            "AWS access key",
            re.compile(
                rf"\b{re.escape(aws_prefix)}"
                r"[A-Z0-9]{16}\b"
            ),
        ),
        (
            "private key material",
            re.compile(
                re.escape(private_key),
                re.IGNORECASE,
            ),
        ),
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


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        relative_parts = path.relative_to(root).parts

        if any(part in IGNORED_DIRECTORIES for part in relative_parts):
            continue

        if path.name in IGNORED_FILE_NAMES or path.name.startswith(".coverage."):
            continue

        yield path


def scan_tree(root: Path) -> list[str]:
    root = root.resolve()
    issues: list[str] = []

    for path in iter_files(root):
        relative = path.relative_to(root)
        suffix = path.suffix.lower()

        if suffix in FORBIDDEN_SUFFIXES:
            issues.append(f"{relative}: forbidden file type {suffix}")
            continue

        if path.name.startswith(".env"):
            issues.append(f"{relative}: environment file forbidden")
            continue

        if suffix not in TEXT_SUFFIXES:
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError as error:
            issues.append(f"{relative}: unreadable file: {error}")
            continue

        for label, pattern in _forbidden_patterns():
            match = pattern.search(text)

            if match is None:
                continue

            line_number = (
                text.count(
                    "\n",
                    0,
                    match.start(),
                )
                + 1
            )

            issues.append(f"{relative}:{line_number}: {label}")

        if suffix != ".csv":
            continue

        try:
            with path.open(
                encoding="utf-8",
                newline="",
            ) as stream:
                header = next(
                    csv.reader(stream),
                    [],
                )
        except OSError as error:
            issues.append(f"{relative}: unreadable CSV: {error}")
            continue

        for column in header:
            lowered = column.lower()

            if any(fragment in lowered for fragment in PRIVATE_COLUMN_FRAGMENTS):
                issues.append(f"{relative}: private column forbidden: {column}")

    return sorted(set(issues))


def build_manifest(
    root: Path,
    output_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    output_path = output_path.resolve()

    files: list[dict[str, Any]] = []

    for path in iter_files(root):
        if path.resolve() == output_path:
            continue

        if path.name == "SHA256SUMS":
            continue

        files.append(
            {
                "path": str(path.relative_to(root)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "generator": "hilmarbench.publication",
        "files": files,
    }

    output_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return manifest


def write_sha256s(
    root: Path,
    output_path: Path,
) -> None:
    root = root.resolve()
    output_path = output_path.resolve()

    lines = []

    for path in iter_files(root):
        if path.resolve() == output_path:
            continue

        lines.append(f"{sha256_file(path)}  {path.relative_to(root)}")

    output_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def verify_manifest(
    root: Path,
    manifest_path: Path,
) -> list[str]:
    root = root.resolve()

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (
        OSError,
        json.JSONDecodeError,
    ) as error:
        return [f"manifest unreadable: {error}"]

    issues: list[str] = []
    entries = manifest.get("files")

    if not isinstance(entries, list):
        return ["manifest files field is not a list"]

    expected_paths: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            issues.append("manifest contains a non-object entry")
            continue

        relative = entry.get("path")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")

        if not isinstance(relative, str):
            issues.append("manifest entry has no valid path")
            continue

        expected_paths.add(relative)
        path = root / relative

        if not path.is_file():
            issues.append(f"{relative}: file missing")
            continue

        if path.stat().st_size != expected_size:
            issues.append(f"{relative}: size mismatch")

        if sha256_file(path) != expected_hash:
            issues.append(f"{relative}: SHA-256 mismatch")

    actual_paths = {
        str(path.relative_to(root))
        for path in iter_files(root)
        if path.name
        not in {
            "SHA256SUMS",
            manifest_path.name,
        }
    }

    for relative in sorted(actual_paths - expected_paths):
        issues.append(f"{relative}: unlisted file")

    for relative in sorted(expected_paths - actual_paths):
        issues.append(f"{relative}: listed but absent")

    return sorted(set(issues))


def _verification_level(
    strategy: str,
) -> str:
    normalized = re.sub(
        r"[^A-Z0-9]+",
        "_",
        strategy.upper(),
    ).strip("_")

    if normalized in {
        "NOSTRA",
        "NOSTRA_AI",
    }:
        return "artifact-verified"

    return "code-reproducible"


def build_public_release(
    metrics_path: Path,
    daily_path: Path,
    output_dir: Path,
    *,
    private_artifact_sha256: str,
) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")

    if not re.fullmatch(
        r"[a-f0-9]{64}",
        private_artifact_sha256,
    ):
        raise ValueError("private_artifact_sha256 must be a lowercase SHA-256 value.")

    metrics = pd.read_csv(metrics_path)
    daily = pd.read_csv(daily_path)

    input_metric_columns = [
        column for column in APPROVED_METRIC_COLUMNS if column != "verification_level"
    ]

    missing_metric_columns = set(input_metric_columns) - set(metrics.columns)

    if missing_metric_columns:
        raise ValueError("Missing metric columns: " + ", ".join(sorted(missing_metric_columns)))

    released_metrics = metrics[input_metric_columns].copy()

    numeric_columns = [
        "cost_bps",
        "observations",
        "final_equity",
        "annualized_volatility",
        "sharpe",
        "maximum_drawdown",
    ]

    for column in numeric_columns:
        released_metrics[column] = pd.to_numeric(
            released_metrics[column],
            errors="raise",
        )

    if (released_metrics["observations"] <= 0).any():
        raise ValueError("observations must be positive.")

    if (released_metrics["final_equity"] <= 0).any():
        raise ValueError("final_equity must be positive.")

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
        released_metrics["strategy"].map(_verification_level),
    )

    timestamp_candidates = [
        column
        for column in daily.columns
        if column.lower()
        in {
            "date",
            "datetime",
            "timestamp",
        }
    ]

    if len(timestamp_candidates) != 1:
        raise ValueError("Exactly one timestamp column is required.")

    timestamp_column = timestamp_candidates[0]
    baseline_columns = [timestamp_column]

    for column in daily.columns:
        lowered = column.lower()

        if column == timestamp_column:
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

        if any(fragment in lowered for fragment in PRIVATE_COLUMN_FRAGMENTS):
            continue

        baseline_columns.append(column)

    if len(baseline_columns) < 3:
        raise ValueError("Insufficient public baseline curves.")

    baseline_daily = daily[baseline_columns].copy()

    output_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    released_metrics[APPROVED_METRIC_COLUMNS].to_csv(
        output_dir / "benchmark_metrics.csv",
        index=False,
    )

    baseline_daily.to_csv(
        output_dir / "baseline_daily_curves.csv",
        index=False,
    )

    methodology = {
        "schema_version": 2,
        "evaluation": {
            "asset": "BTC",
            "frequency": "daily",
            "date_start": str(released_metrics["date_start"].iloc[0]),
            "date_end": str(released_metrics["date_end"].iloc[0]),
            "transaction_cost_bps": float(released_metrics["cost_bps"].iloc[0]),
            "initial_position": 0.0,
            "turnover_mode": "raw",
            "dynamic_signal_lag_days": 1,
            "annualization_factor": 365.0,
            "cagr_formula": ("final_equity ** (365 / observations) - 1"),
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

    (output_dir / "methodology.json").write_text(
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
        "private_evaluation_artifact_sha256": (private_artifact_sha256),
        "disclosure": ("The committed evaluation artifact is retained privately."),
    }

    (output_dir / "nostra_artifact_commitment.json").write_text(
        json.dumps(
            commitment,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    build_manifest(
        output_dir,
        output_dir / "manifest.json",
    )

    write_sha256s(
        output_dir,
        output_dir / "SHA256SUMS",
    )


def verify_release(
    root: Path,
) -> list[str]:
    issues: list[str] = []

    actual_files = {path.name for path in root.iterdir() if path.is_file()}

    for name in sorted(APPROVED_RELEASE_FILES - actual_files):
        issues.append(f"{name}: required release file missing")

    for name in sorted(actual_files - APPROVED_RELEASE_FILES):
        issues.append(f"{name}: unexpected release file")

    metrics_path = root / "benchmark_metrics.csv"

    if metrics_path.is_file():
        metrics = pd.read_csv(metrics_path)

        if list(metrics.columns) != (APPROVED_METRIC_COLUMNS):
            issues.append("benchmark_metrics.csv: invalid schema")
        else:
            normalized = (
                metrics["strategy"]
                .astype(str)
                .str.upper()
                .str.replace(
                    r"[^A-Z0-9]+",
                    "_",
                    regex=True,
                )
                .str.strip("_")
            )

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
                issues.append("benchmark_metrics.csv: invalid Nostra verification")

            baselines = metrics.loc[
                ~normalized.isin(
                    {
                        "NOSTRA",
                        "NOSTRA_AI",
                    }
                )
            ]

            if set(baselines["verification_level"]) != {"code-reproducible"}:
                issues.append("benchmark_metrics.csv: invalid baseline verification")

    daily_path = root / "baseline_daily_curves.csv"

    if daily_path.is_file():
        daily = pd.read_csv(
            daily_path,
            nrows=1,
        )

        timestamp_count = sum(
            column.lower()
            in {
                "date",
                "datetime",
                "timestamp",
            }
            for column in daily.columns
        )

        if timestamp_count != 1:
            issues.append("baseline_daily_curves.csv: invalid timestamp surface")

        for column in daily.columns:
            lowered = column.lower()

            if lowered.startswith("nostra"):
                issues.append(f"baseline_daily_curves.csv: Nostra time series forbidden: {column}")

            if lowered not in {
                "date",
                "datetime",
                "timestamp",
            } and not lowered.endswith(
                (
                    "_equity",
                    "_drawdown",
                )
            ):
                issues.append(f"baseline_daily_curves.csv: unexpected column: {column}")

            if any(fragment in lowered for fragment in PRIVATE_COLUMN_FRAGMENTS):
                issues.append(f"baseline_daily_curves.csv: private column forbidden: {column}")

    methodology_path = root / "methodology.json"

    if methodology_path.is_file():
        try:
            methodology = json.loads(methodology_path.read_text(encoding="utf-8"))

            nostra = methodology.get(
                "nostra",
                {},
            )

            for key in (
                "model_code_in_github",
                "daily_equity_in_github",
                "daily_positions_public",
                "daily_returns_public",
                "turnover_public",
            ):
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
            issues.append(f"methodology.json: unreadable: {error}")

    commitment_path = root / "nostra_artifact_commitment.json"

    if commitment_path.is_file():
        try:
            commitment = json.loads(commitment_path.read_text(encoding="utf-8"))

            value = commitment.get("private_evaluation_artifact_sha256")

            if not isinstance(value, str) or not re.fullmatch(
                r"[a-f0-9]{64}",
                value,
            ):
                issues.append("nostra_artifact_commitment.json: invalid SHA-256 commitment")

        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            issues.append(f"nostra_artifact_commitment.json: unreadable: {error}")

    issues.extend(scan_tree(root))

    manifest_path = root / "manifest.json"

    if manifest_path.is_file():
        issues.extend(
            verify_manifest(
                root,
                manifest_path,
            )
        )

    return sorted(set(issues))
