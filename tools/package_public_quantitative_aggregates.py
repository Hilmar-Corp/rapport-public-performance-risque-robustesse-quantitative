"""Build or verify public quantitative aggregate exports."""

from __future__ import annotations

import argparse
from pathlib import Path

from hilmarbench.quantitative_exports import (
    build_public_quantitative_export,
    verify_public_quantitative_export,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Package or verify an already-sanitized public quantitative aggregate payload."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    build = subparsers.add_parser("build")
    build.add_argument(
        "--input",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )

    verify = subparsers.add_parser("verify")
    verify.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "build":
        build_public_quantitative_export(
            args.input,
            args.output_dir,
        )
        print(
            "Public quantitative aggregate export built:",
            args.output_dir,
        )
        return

    issues = verify_public_quantitative_export(args.output_dir)

    if issues:
        for issue in issues:
            print(
                "ERROR:",
                issue,
            )
        raise SystemExit(1)

    print("Public quantitative aggregate export verification: PASS")


if __name__ == "__main__":
    main()
