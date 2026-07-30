from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "sbom",
        type=Path,
    )

    return parser.parse_args()


def component_identity(
    component: dict[str, Any],
) -> tuple[str, str]:
    return (
        str(component.get("name", "")),
        str(component.get("version", "")),
    )


def main() -> None:
    args = parse_args()

    data = json.loads(args.sbom.read_text(encoding="utf-8"))

    if data.get("bomFormat") != "CycloneDX":
        raise SystemExit("SBOM is not CycloneDX.")

    components = data.get("components")

    if (
        not isinstance(
            components,
            list,
        )
        or not components
    ):
        raise SystemExit("SBOM contains no dependency component.")

    identities = {
        component_identity(component) for component in components if isinstance(component, dict)
    }

    if len(identities) != len(components):
        raise SystemExit("SBOM contains duplicate or invalid components.")

    print(f"CYCLONEDX SBOM VALIDATED: {len(identities)} components")


if __name__ == "__main__":
    main()
