from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a release evidence manifest linking source, container and public artifacts."
        ),
    )
    parser.add_argument(
        "--release-dir",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--source-commit",
        required=True,
    )
    parser.add_argument(
        "--source-tag",
        required=True,
    )
    parser.add_argument(
        "--workflow-run",
        required=True,
    )
    parser.add_argument(
        "--base-image",
        required=True,
    )
    parser.add_argument(
        "--image-reference",
        required=True,
    )
    parser.add_argument(
        "--image-digest",
        required=True,
    )
    parser.add_argument(
        "--constraints",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--cyclonedx",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--spdx",
        type=Path,
        required=True,
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


def file_record(path: Path) -> dict[str, object]:
    return {
        "name": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def main() -> int:
    args = parse_args()
    release_dir = args.release_dir.resolve()

    release_files = [file_record(path) for path in sorted(release_dir.iterdir()) if path.is_file()]

    payload = {
        "schema_version": 1,
        "source": {
            "commit": args.source_commit,
            "tag": args.source_tag,
            "workflow_run": args.workflow_run,
        },
        "container": {
            "base_image": args.base_image,
            "image_reference": args.image_reference,
            "image_digest": args.image_digest,
        },
        "environment": {
            "constraints": file_record(
                args.constraints.resolve(),
            ),
            "cyclonedx_sbom": file_record(
                args.cyclonedx.resolve(),
            ),
            "spdx_sbom": file_record(
                args.spdx.resolve(),
            ),
        },
        "public_release": {
            "directory": args.release_dir.as_posix(),
            "files": release_files,
        },
        "proprietary_boundary": {
            "nostra_model_code_included": False,
            "nostra_daily_positions_included": False,
            "nostra_daily_returns_included": False,
            "nostra_features_included": False,
        },
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Provenance manifest: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
