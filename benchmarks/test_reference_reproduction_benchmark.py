from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Final

import pytest

ROOT: Final = Path(__file__).resolve().parents[1]


def reproduce_reference_release() -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": "src",
            "TZ": "UTC",
            "PYTHONHASHSEED": "0",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )

    return subprocess.run(
        [
            sys.executable,
            "tools/reproduce_reference_release.py",
            "--release-dir",
            "artifacts/latest",
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.mark.benchmark
def test_reference_release_reproduction_benchmark(
    benchmark: Any,
) -> None:
    result = benchmark.pedantic(
        reproduce_reference_release,
        rounds=1,
        iterations=1,
        warmup_rounds=0,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
