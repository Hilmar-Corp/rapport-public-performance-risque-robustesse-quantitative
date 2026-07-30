from __future__ import annotations

import argparse
from pathlib import Path

from hilmarbench.publication import (
    build_public_release,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Build a sanitized HilmarCorp public release candidate.")
    )

    parser.add_argument(
        "--metrics",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--daily",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--private-artifact-sha256",
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_public_release(
        args.metrics,
        args.daily,
        args.output,
        private_artifact_sha256=(args.private_artifact_sha256),
    )

    print("PUBLIC RELEASE CANDIDATE BUILT")
    print(args.output)


if __name__ == "__main__":
    main()
