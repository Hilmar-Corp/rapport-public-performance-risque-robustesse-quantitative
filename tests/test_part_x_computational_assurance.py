from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "generate_part_x_computational_assurance.py"
SUMMARY_PATH = (
    ROOT
    / "artifacts"
    / "report_support"
    / "part_x_assurance"
    / "part_x_computational_assurance_summary.json"
)
MANIFEST_PATH = ROOT / "artifacts" / "report_support" / "part_x_assurance" / "manifest.json"


def load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "generate_part_x_computational_assurance",
        SCRIPT_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def test_part_x_summary_contract() -> None:
    generator = load_generator()

    summary = generator.build_summary(test_count=1)

    assert summary["model"] == "Nostra AI V5.246"
    assert summary["source_release"] == "v0.3.0"

    quality = summary["automated_quality"]

    assert quality["branch_coverage_required"] is True
    assert quality["coverage_fail_under_percent"] == 100
    assert quality["pyright_mode"] == "strict"

    evidence = summary["evidence_classes"]

    assert evidence["public_benchmarks"] == "code-reproducible"
    assert evidence["nostra_aggregated_results"] == "artifact-verified"
    assert evidence["external_independent_validation"] == "not_claimed"


def test_independent_recalculation_is_numerically_reconciled() -> None:
    summary = json.loads(
        SUMMARY_PATH.read_text(
            encoding="utf-8",
        )
    )

    recalculation = summary["independent_accounting_recalculation"]

    assert recalculation["official_return_maximum_absolute_difference"] < 1e-12
    assert recalculation["official_equity_maximum_absolute_difference"] < 1e-10

    for difference in recalculation["maximum_aggregate_absolute_differences"].values():
        assert float(difference) < 1e-8


def test_part_x_manifest_matches_controlled_files() -> None:
    manifest = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8",
        )
    )

    assert manifest["source_release"] == "v0.3.0"

    for record in manifest["files"]:
        path = ROOT / record["path"]

        assert path.is_file()
        assert path.stat().st_size == record["size_bytes"]
        assert sha256_file(path) == record["sha256"]
