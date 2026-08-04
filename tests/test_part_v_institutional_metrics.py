from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

GENERATOR = ROOT / "tools" / "generate_part_v_institutional_metrics.py"
SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_v"
METRICS_PATH = SUPPORT_DIR / "part_v_institutional_metrics.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"
MARKDOWN_PATH = ROOT / "docs" / "tables" / "part_v_institutional_metrics.md"

OBSERVATIONS = 2211
ANNUALIZATION = 365.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def load_horizons() -> dict[str, dict[str, object]]:
    payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    return {str(record["horizon"]): record for record in payload["performance_horizons"]}


@pytest.mark.parametrize(
    ("horizon", "nostra", "bitcoin", "active"),
    [
        (
            "2026 YTD",
            -0.011301710194350556,
            -0.23206654966866014,
            0.22076483947430958,
        ),
        (
            "1 an",
            -0.05713928784439537,
            -0.3641670316997264,
            0.30702774385533105,
        ),
        (
            "3 ans annualisés",
            0.4073078654305191,
            0.35151216855780043,
            0.05579569687271868,
        ),
        (
            "5 ans annualisés",
            0.3479417143490646,
            0.12362246280015987,
            0.22431925154890475,
        ),
        (
            "Depuis l'origine annualisé",
            0.5245366668238287,
            0.38567198239297795,
            0.13886468443085076,
        ),
        (
            "Depuis l'origine cumulé",
            11.863641976380386,
            6.212950328296465,
            5.650691648083921,
        ),
    ],
)
def test_controlled_performance_horizons(
    horizon: str,
    nostra: float,
    bitcoin: float,
    active: float,
) -> None:
    record = load_horizons()[horizon]

    assert float(record["nostra_return"]) == pytest.approx(
        nostra,
        rel=1e-12,
        abs=1e-15,
    )
    assert float(record["bitcoin_return"]) == pytest.approx(
        bitcoin,
        rel=1e-12,
        abs=1e-15,
    )
    assert float(record["active_return"]) == pytest.approx(
        active,
        rel=1e-12,
        abs=1e-15,
    )


def test_inception_cagr_uses_2211_observations() -> None:
    horizons = load_horizons()

    annualized = horizons["Depuis l'origine annualisé"]
    cumulative = horizons["Depuis l'origine cumulé"]

    nostra_growth = 1.0 + float(cumulative["nostra_return"])
    bitcoin_growth = 1.0 + float(cumulative["bitcoin_return"])

    expected_nostra = nostra_growth ** (ANNUALIZATION / OBSERVATIONS) - 1.0
    expected_bitcoin = bitcoin_growth ** (ANNUALIZATION / OBSERVATIONS) - 1.0

    incorrect_nostra_2210 = nostra_growth ** (ANNUALIZATION / 2210) - 1.0
    incorrect_bitcoin_2210 = bitcoin_growth ** (ANNUALIZATION / 2210) - 1.0

    observed_nostra = float(annualized["nostra_return"])
    observed_bitcoin = float(annualized["bitcoin_return"])

    assert observed_nostra == pytest.approx(
        expected_nostra,
        rel=1e-12,
        abs=1e-15,
    )
    assert observed_bitcoin == pytest.approx(
        expected_bitcoin,
        rel=1e-12,
        abs=1e-15,
    )

    assert not math.isclose(
        observed_nostra,
        incorrect_nostra_2210,
        rel_tol=1e-12,
        abs_tol=1e-15,
    )
    assert not math.isclose(
        observed_bitcoin,
        incorrect_bitcoin_2210,
        rel_tol=1e-12,
        abs_tol=1e-15,
    )


def test_generator_uses_controlled_365_day_convention() -> None:
    source = GENERATOR.read_text(encoding="utf-8")

    assert "365.25" not in source
    assert "365.0 / annualization_denominator" in source
    assert "len(data) if inception_base else elapsed_days" in source


def test_markdown_contains_corrected_horizons() -> None:
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")

    expected_rows = {
        "| 3 ans annualisés | 40,73 % | 35,15 % | +5,58 pts |",
        "| 5 ans annualisés | 34,79 % | 12,36 % | +22,43 pts |",
        ("| Depuis l'origine annualisé | 52,45 % | 38,57 % | +13,89 pts |"),
        ("| Depuis l'origine cumulé | 1186,36 % | 621,30 % | +565,07 pts |"),
    }

    for row in expected_rows:
        assert row in markdown


def test_part_v_manifest_and_checksums_are_reconciled() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    manifest_records = {str(record["path"]): record for record in manifest["files"]}

    checksum_records: dict[str, str] = {}

    for line in CHECKSUMS_PATH.read_text(encoding="utf-8").splitlines():
        digest, relative_path = line.split(maxsplit=1)
        checksum_records[relative_path] = digest

    assert set(checksum_records) == set(manifest_records)

    for relative_path, record in manifest_records.items():
        path = ROOT / relative_path

        assert path.is_file()
        assert int(record["size_bytes"]) == path.stat().st_size
        assert str(record["sha256"]) == sha256_file(path)
        assert checksum_records[relative_path] == sha256_file(path)
