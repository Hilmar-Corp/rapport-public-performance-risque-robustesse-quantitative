from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
MATRIX: Final = ROOT / "governance" / "quantitative_validation_control_matrix.csv"
COMMITMENTS: Final = ROOT / "governance" / "quantitative_evidence_commitments.csv"

PUBLIC_COMMITMENT_SCHEME: Final = "sha256-canonical-public-evidence-v2"
HISTORICAL_PRIVATE_COMMITMENT_SCHEME: Final = "sha256-canonical-json-v1"

COMMITMENT_FIELDS: Final = (
    "control_id",
    "public_evidence_items",
    "public_evidence_commitment_sha256",
    "public_commitment_scheme",
    "private_evidence_items",
    "private_evidence_commitment_sha256",
    "private_commitment_scheme",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Generate or verify reproducible public quantitative evidence commitments."),
    )

    mode = parser.add_mutually_exclusive_group(
        required=True,
    )
    mode.add_argument(
        "--write",
        action="store_true",
    )
    mode.add_argument(
        "--check",
        action="store_true",
    )

    return parser.parse_args()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def canonical_json_bytes(
    payload: object,
) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def directory_record(
    path: Path,
) -> dict[str, object]:
    files = sorted(candidate for candidate in path.rglob("*") if candidate.is_file())

    child_records = sorted(
        (
            {
                "sha256": sha256_file(candidate),
                "type": "file",
            }
            for candidate in files
        ),
        key=lambda item: str(item["sha256"]),
    )

    return {
        "file_count": len(files),
        "sha256": sha256_bytes(canonical_json_bytes(child_records)),
        "type": "directory",
    }


def evidence_record(
    path: Path,
) -> dict[str, object]:
    if path.is_file():
        return {
            "sha256": sha256_file(path),
            "type": "file",
        }

    if path.is_dir():
        return directory_record(path)

    raise ValueError(f"Public evidence does not exist: {path}")


def parse_public_evidence(
    raw_value: str,
) -> list[Path]:
    references: list[Path] = []

    for raw_reference in raw_value.split(";"):
        reference = raw_reference.strip()

        if not reference:
            continue

        candidate = Path(reference)

        if candidate.is_absolute():
            raise ValueError(f"Public evidence paths must be repository-relative: {reference}")

        resolved = (ROOT / candidate).resolve()

        if ROOT not in resolved.parents:
            raise ValueError(f"Public evidence escapes the repository: {reference}")

        references.append(resolved)

    return references


def public_commitment(
    control_id: str,
    references: list[Path],
) -> tuple[int, str]:
    items = sorted(
        (evidence_record(path) for path in references),
        key=lambda item: (
            str(item["type"]),
            str(item["sha256"]),
            int(item.get("file_count", 0)),
        ),
    )

    if not items:
        return 0, ""

    payload = {
        "control_id": control_id,
        "evidence": items,
        "scope": "public",
        "schema_version": 2,
    }

    return (
        len(items),
        sha256_bytes(canonical_json_bytes(payload)),
    )


def read_csv(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def expected_rows() -> list[dict[str, str]]:
    matrix_rows = read_csv(MATRIX)
    existing_rows = {row["control_id"]: row for row in read_csv(COMMITMENTS)}

    output: list[dict[str, str]] = []

    for matrix_row in matrix_rows:
        control_id = matrix_row["control_id"]
        existing = existing_rows[control_id]

        references = parse_public_evidence(matrix_row["public_evidence"])
        public_count, public_hash = public_commitment(
            control_id,
            references,
        )

        private_count = int(existing["private_evidence_items"])
        private_hash = existing["private_evidence_commitment_sha256"]

        if bool(private_hash) is not (private_count > 0):
            raise ValueError(f"Invalid historical private commitment for {control_id}.")

        output.append(
            {
                "control_id": control_id,
                "public_evidence_items": str(public_count),
                "public_evidence_commitment_sha256": (public_hash),
                "public_commitment_scheme": (PUBLIC_COMMITMENT_SCHEME if public_count > 0 else ""),
                "private_evidence_items": str(private_count),
                "private_evidence_commitment_sha256": (private_hash),
                "private_commitment_scheme": (
                    HISTORICAL_PRIVATE_COMMITMENT_SCHEME if private_count > 0 else ""
                ),
            }
        )

    return output


def render_csv(
    rows: list[dict[str, str]],
) -> str:
    from io import StringIO

    output = StringIO(
        newline="",
    )
    writer = csv.DictWriter(
        output,
        fieldnames=COMMITMENT_FIELDS,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue()


def main() -> int:
    args = parse_args()
    expected = render_csv(expected_rows())

    if args.write:
        COMMITMENTS.write_text(
            expected,
            encoding="utf-8",
            newline="\n",
        )
        print("PUBLIC QUANTITATIVE COMMITMENTS UPDATED")
        return 0

    current = COMMITMENTS.read_text(
        encoding="utf-8-sig",
    )

    if current != expected:
        print("PUBLIC QUANTITATIVE COMMITMENT VERIFICATION FAILED")
        return 1

    print("PUBLIC QUANTITATIVE COMMITMENT VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
