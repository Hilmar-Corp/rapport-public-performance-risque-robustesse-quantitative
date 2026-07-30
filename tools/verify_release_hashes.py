from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify all checksums listed in a controlled release.",
    )
    parser.add_argument(
        "release_dir",
        type=Path,
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def verify_release(root: Path) -> list[str]:
    issues: list[str] = []
    checksums_path = root / "SHA256SUMS"

    if not checksums_path.is_file():
        return ["SHA256SUMS: missing"]

    entries: dict[str, str] = {}

    for line_number, raw_line in enumerate(
        checksums_path.read_text(
            encoding="utf-8",
        ).splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        parts = line.split(maxsplit=1)

        if len(parts) != 2:
            issues.append(f"SHA256SUMS:{line_number}: invalid entry")
            continue

        expected, relative_name = parts
        relative_name = relative_name.lstrip("*")

        if not SHA256_PATTERN.fullmatch(expected):
            issues.append(f"SHA256SUMS:{line_number}: invalid digest")
            continue

        if relative_name in entries:
            issues.append(f"SHA256SUMS:{line_number}: duplicate path")
            continue

        entries[relative_name] = expected

    for relative_name, expected in sorted(entries.items()):
        path = root / relative_name

        if not path.is_file():
            issues.append(f"{relative_name}: missing")
            continue

        actual = sha256(path)

        if actual != expected:
            issues.append(f"{relative_name}: digest mismatch")

    return issues


def main() -> int:
    args = parse_args()
    root = args.release_dir.resolve()
    issues = verify_release(root)

    if issues:
        print("RELEASE HASH VERIFICATION FAILED")

        for issue in issues:
            print(f"- {issue}")

        return 1

    print("RELEASE HASH VERIFICATION PASSED")
    print(f"Release: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
