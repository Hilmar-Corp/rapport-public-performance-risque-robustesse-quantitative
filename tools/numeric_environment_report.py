from __future__ import annotations

import json
import locale
import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Final

OUTPUT_PATH: Final = Path("artifacts/numeric_environment_report.json")

PACKAGES: Final[tuple[str, ...]] = (
    "numpy",
    "pandas",
    "scipy",
    "arch",
    "hmmlearn",
    "scikit-learn",
)


def package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def main() -> int:
    report: dict[str, object] = {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "locale": {
            "preferred_encoding": locale.getpreferredencoding(False),
            "locale": locale.setlocale(locale.LC_ALL, None),
        },
        "environment": {
            "TZ": os.environ.get("TZ"),
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
            "NUMEXPR_NUM_THREADS": os.environ.get("NUMEXPR_NUM_THREADS"),
        },
        "packages": {package: package_version(package) for package in PACKAGES},
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
