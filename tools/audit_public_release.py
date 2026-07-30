from __future__ import annotations

import argparse
from pathlib import Path

from hilmarbench.publication import (
    scan_tree,
    verify_release,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Audit a public repository or a built release candidate.")
    )

    parser.add_argument(
        "--root",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--release",
        action="store_true",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()

    issues = verify_release(root) if args.release else scan_tree(root)

    if issues:
        print("PUBLICATION GATE FAILED")
        print()

        for issue in issues:
            print(f"- {issue}")

        raise SystemExit(1)

    print("PUBLICATION GATE PASSED")


if __name__ == "__main__":
    main()
