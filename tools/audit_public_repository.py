from __future__ import annotations

import argparse
import csv
import re
from collections.abc import Iterator
from pathlib import Path

from hilmarbench.publication import (
    IGNORED_DIRECTORIES,
    scan_tree,
)

ALLOWED_CSV_PATHS = {
    Path("artifacts/latest/baseline_daily_curves.csv"),
    Path("artifacts/latest/benchmark_metrics.csv"),
    Path("artifacts/releases/v0.2.0/baseline_daily_curves.csv"),
    Path("artifacts/releases/v0.2.0/benchmark_metrics.csv"),
    Path("artifacts/releases/v0.2.1/baseline_daily_curves.csv"),
    Path("artifacts/releases/v0.2.1/benchmark_metrics.csv"),
    Path("governance/quantitative_evidence_commitments.csv"),
    Path("governance/quantitative_validation_control_matrix.csv"),
}

CONTROLLED_CSV_SCHEMAS = {
    Path("governance/quantitative_validation_control_matrix.csv"): (
        "control_id",
        "domain",
        "control_question",
        "method",
        "public_status",
        "gap",
        "public_evidence",
        "private_evidence_commitment_sha256",
        "ip_classification",
        "limitation",
    ),
    Path("governance/quantitative_evidence_commitments.csv"): (
        "control_id",
        "public_evidence_items",
        "public_evidence_commitment_sha256",
        "public_commitment_scheme",
        "private_evidence_items",
        "private_evidence_commitment_sha256",
        "private_commitment_scheme",
    ),
}


FORBIDDEN_REPOSITORY_NAME_PATTERNS = (
    re.compile(
        r"^nostra.*"
        r"(?:daily|monthly|curve|position|return)"
        r".*\.csv$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:site|website).*chart.*"
        r"\.(?:csv|json)$",
        re.IGNORECASE,
    ),
)

FORBIDDEN_NOSTRA_HEADER_FRAGMENTS = {
    "nostra_equity",
    "nostra_drawdown",
    "nostra_position",
    "nostra_return",
    "nostra_turnover",
    "nostra_cost",
    "nostra_probability",
    "nostra_feature",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Audit the complete public repository before publication.")
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def repository_root(
    requested: Path | None,
) -> Path:
    if requested is not None:
        return requested.resolve()

    return Path(__file__).resolve().parents[1]


def iter_repository_files(
    root: Path,
) -> Iterator[tuple[Path, Path]]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        relative = path.relative_to(root)

        if any(part in IGNORED_DIRECTORIES for part in relative.parts):
            continue

        if (
            path.name == ".coverage"
            or path.name.startswith(".coverage.")
            or path.name == "coverage.xml"
        ):
            continue

        yield path, relative


def is_forbidden_repository_name(
    name: str,
) -> bool:
    return any(pattern.search(name) is not None for pattern in FORBIDDEN_REPOSITORY_NAME_PATTERNS)


def audit_repository(
    root: Path,
) -> list[str]:
    issues = list(scan_tree(root))

    for path, relative in iter_repository_files(root):
        if is_forbidden_repository_name(path.name):
            issues.append(f"{relative}: forbidden repository file")

        if path.suffix.lower() != ".csv":
            continue

        if relative not in ALLOWED_CSV_PATHS:
            issues.append(f"{relative}: uncontrolled CSV forbidden")
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

        expected_header = CONTROLLED_CSV_SCHEMAS.get(relative)

        if expected_header is not None and tuple(header) != expected_header:
            issues.append(f"{relative}: invalid controlled CSV schema")
            continue

        if relative.name != ("baseline_daily_curves.csv"):
            continue

        for column in header:
            lowered = column.lower()

            if any(fragment in lowered for fragment in FORBIDDEN_NOSTRA_HEADER_FRAGMENTS):
                issues.append(f"{relative}: forbidden Nostra time-series column: {column}")

    for relative in sorted(ALLOWED_CSV_PATHS):
        path = root / relative

        if not path.is_file():
            issues.append(f"{relative}: required controlled artifact missing")

    return sorted(set(issues))


def main() -> None:
    args = parse_args()
    root = repository_root(args.root)

    issues = audit_repository(root)

    if issues:
        print("PUBLICATION AUDIT FAILED")

        for issue in issues:
            print(f"- {issue}")

        raise SystemExit(1)

    print("PUBLICATION AUDIT PASSED")


if __name__ == "__main__":
    main()
