from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path
from urllib.parse import quote


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Generate CycloneDX and SPDX inventories from the active Python environment."),
    )
    parser.add_argument(
        "--cyclonedx-output",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--spdx-output",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--source-name",
        default="hilmarcorp-benchmark-suite",
    )
    parser.add_argument(
        "--source-version",
        required=True,
    )
    return parser.parse_args()


def timestamp() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")

    instant = datetime.fromtimestamp(int(epoch), tz=UTC) if epoch is not None else datetime.now(UTC)

    return (
        instant.replace(
            microsecond=0,
        )
        .isoformat()
        .replace("+00:00", "Z")
    )


def normalize_name(value: str) -> str:
    return value.lower().replace("_", "-")


def package_inventory() -> list[dict[str, str]]:
    packages: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    for distribution in distributions():
        name = distribution.metadata.get("Name") or "unknown"
        version = distribution.version
        normalized = normalize_name(name)

        license_value = (
            distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or "NOASSERTION"
        ).strip()

        if not license_value:
            license_value = "NOASSERTION"

        purl = (
            "pkg:pypi/"
            + quote(
                normalized,
                safe=".-_",
            )
            + "@"
            + quote(
                version,
                safe=".-_+",
            )
        )

        packages[(normalized, version)] = {
            "name": name,
            "normalized_name": normalized,
            "version": version,
            "license": license_value,
            "purl": purl,
        }

    return [packages[key] for key in sorted(packages)]


def stable_identifier(
    source_name: str,
    source_version: str,
    packages: list[dict[str, str]],
) -> uuid.UUID:
    material = json.dumps(
        {
            "source": source_name,
            "version": source_version,
            "packages": [
                (
                    package["normalized_name"],
                    package["version"],
                )
                for package in packages
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        material.encode("utf-8"),
    ).hexdigest()

    return uuid.uuid5(
        uuid.NAMESPACE_URL,
        digest,
    )


def build_cyclonedx(
    source_name: str,
    source_version: str,
    packages: list[dict[str, str]],
    identifier: uuid.UUID,
) -> dict[str, object]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{identifier}",
        "version": 1,
        "metadata": {
            "timestamp": timestamp(),
            "component": {
                "type": "application",
                "name": source_name,
                "version": source_version,
                "bom-ref": (f"pkg:pypi/{source_name}@{source_version}"),
            },
        },
        "components": [
            {
                "type": "library",
                "name": package["name"],
                "version": package["version"],
                "purl": package["purl"],
                "bom-ref": package["purl"],
                "licenses": [
                    {
                        "license": {
                            "name": package["license"],
                        }
                    }
                ],
            }
            for package in packages
        ],
    }


def build_spdx(
    source_name: str,
    source_version: str,
    packages: list[dict[str, str]],
    identifier: uuid.UUID,
) -> dict[str, object]:
    spdx_packages: list[dict[str, object]] = []
    relationships: list[dict[str, str]] = []

    for index, package in enumerate(
        packages,
        start=1,
    ):
        package_id = f"SPDXRef-Package-{index}"

        spdx_packages.append(
            {
                "SPDXID": package_id,
                "name": package["name"],
                "versionInfo": package["version"],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": package["license"],
                "copyrightText": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": ("PACKAGE-MANAGER"),
                        "referenceType": "purl",
                        "referenceLocator": (package["purl"]),
                    }
                ],
            }
        )

        relationships.append(
            {
                "spdxElementId": ("SPDXRef-DOCUMENT"),
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": package_id,
            }
        )

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{source_name}-{source_version}",
        "documentNamespace": (
            f"https://hilmar-corp.com/spdx/{source_name}/{source_version}/{identifier}"
        ),
        "creationInfo": {
            "created": timestamp(),
            "creators": [
                "Organization: HilmarCorp",
                ("Tool: HilmarCorp Python SBOM generator-1"),
            ],
        },
        "packages": spdx_packages,
        "relationships": relationships,
    }


def write_json(
    path: Path,
    payload: dict[str, object],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    packages = package_inventory()

    identifier = stable_identifier(
        args.source_name,
        args.source_version,
        packages,
    )

    write_json(
        args.cyclonedx_output,
        build_cyclonedx(
            args.source_name,
            args.source_version,
            packages,
            identifier,
        ),
    )

    write_json(
        args.spdx_output,
        build_spdx(
            args.source_name,
            args.source_version,
            packages,
            identifier,
        ),
    )

    print(f"Generated {len(packages)} package records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
