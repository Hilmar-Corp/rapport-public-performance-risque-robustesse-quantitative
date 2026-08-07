from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_x_assurance"
SUMMARY_PATH = SUPPORT_DIR / "part_x_computational_assurance_summary.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

TABLE_PATH = ROOT / "docs" / "tables" / "part_x_computational_assurance_results.md"
GENERATOR_PATH = ROOT / "tools" / "generate_part_x_computational_assurance.py"
TEST_PATH = ROOT / "tests" / "test_part_x_computational_assurance.py"

INDEPENDENT_RECALCULATION_PATH = (
    ROOT
    / "artifacts"
    / "report_support"
    / "part_x"
    / "independent_accounting_recalculation_summary.json"
)

QUALITY_WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"
HARDENING_WORKFLOW = ROOT / ".github" / "workflows" / "quant-hardening.yml"
OCI_WORKFLOW = ROOT / ".github" / "workflows" / "oci-reproduction.yml"
CODEQL_WORKFLOW = ROOT / ".github" / "workflows" / "codeql.yml"
DEPENDENCY_REVIEW_WORKFLOW = ROOT / ".github" / "workflows" / "dependency-review.yml"
SECURITY_WORKFLOW = ROOT / ".github" / "workflows" / "security.yml"
PROVENANCE_WORKFLOW = ROOT / ".github" / "workflows" / "release-provenance.yml"
RESILIENCE_WORKFLOW = ROOT / ".github" / "workflows" / "repository-resilience.yml"

MODEL = "Nostra AI V5.246"
SOURCE_RELEASE = "v0.3.0"

CONTROLLED_EVIDENCE_PATHS = [
    ROOT / "pyproject.toml",
    ROOT / "Makefile",
    ROOT / "Dockerfile",
    ROOT / "REPRODUCIBILITY.md",
    ROOT / "PROPRIETARY_BOUNDARY.md",
    ROOT / "CHANGE_CONTROL.md",
    ROOT / "docs" / "RELEASE_EVIDENCE.md",
    ROOT / "requirements" / "constraints-py313.txt",
    QUALITY_WORKFLOW,
    HARDENING_WORKFLOW,
    OCI_WORKFLOW,
    CODEQL_WORKFLOW,
    DEPENDENCY_REVIEW_WORKFLOW,
    SECURITY_WORKFLOW,
    PROVENANCE_WORKFLOW,
    RESILIENCE_WORKFLOW,
    ROOT / "scripts" / "backup_repository.sh",
    ROOT / "scripts" / "verify_repository_backup.sh",
    INDEPENDENT_RECALCULATION_PATH,
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def require_paths() -> None:
    missing = [
        path.relative_to(ROOT).as_posix() for path in CONTROLLED_EVIDENCE_PATHS if not path.exists()
    ]

    if missing:
        raise RuntimeError("Preuves contrôlées manquantes:\n- " + "\n- ".join(missing))


def collect_pytest_items() -> int:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-o",
            "addopts=",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Impossible de collecter les tests.\n" + result.stdout + "\n" + result.stderr
        )

    node_ids = [
        line.strip()
        for line in result.stdout.splitlines()
        if "::" in line and not line.startswith("=")
    ]

    if not node_ids:
        raise RuntimeError("Aucun test pytest collecté.")

    return len(node_ids)


def parse_python_matrix() -> dict[str, Any]:
    quality = read_text(QUALITY_WORKFLOW)

    versions = sorted(
        set(
            re.findall(
                r'python-version:\s*"([^"]+)"',
                quality,
            )
        )
    )

    systems = sorted(
        set(
            match.strip()
            for match in re.findall(
                r"- os:\s*([^\n]+)",
                quality,
            )
        )
    )

    return {
        "python_versions": versions,
        "operating_systems": systems,
        "canonical_python": "3.13",
    }


def build_summary(test_count: int | None = None) -> dict[str, Any]:
    require_paths()

    if test_count is None:
        test_count = collect_pytest_items()

    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)

    pytest_config = pyproject["tool"]["pytest"]["ini_options"]
    addopts = list(pytest_config["addopts"])
    pyright = pyproject["tool"]["pyright"]
    ruff = pyproject["tool"]["ruff"]

    coverage_threshold = None

    for option in addopts:
        if option.startswith("--cov-fail-under="):
            coverage_threshold = int(option.split("=", maxsplit=1)[1])

    if coverage_threshold is None:
        raise RuntimeError("Seuil de couverture introuvable.")

    independent = read_json(INDEPENDENT_RECALCULATION_PATH)
    reconciliation = independent["reconciliation"]

    public_modules = sorted(
        path.name for path in (ROOT / "src" / "hilmarbench").glob("*.py") if path.is_file()
    )

    reproducibility = read_text(ROOT / "REPRODUCIBILITY.md")

    for label in [
        "code-reproducible",
        "artifact-verified",
        "private-controlled",
        "independent validation",
    ]:
        if label not in reproducibility:
            raise RuntimeError(f"Classe de preuve absente de REPRODUCIBILITY.md: {label}")

    provenance = read_text(PROVENANCE_WORKFLOW).lower()

    required_features = [
        "cyclonedx",
        "spdx",
        "attest-build-provenance",
        "id-token: write",
        "ghcr",
    ]

    missing_features = [feature for feature in required_features if feature not in provenance]

    if missing_features:
        raise RuntimeError("Éléments de provenance manquants: " + ", ".join(missing_features))

    resilience = read_text(RESILIENCE_WORKFLOW)

    if "backup_repository.sh" not in resilience:
        raise RuntimeError("Commande de sauvegarde absente.")

    if "verify_repository_backup.sh" not in resilience:
        raise RuntimeError("Commande de restauration absente.")

    workflow_paths = [
        QUALITY_WORKFLOW,
        HARDENING_WORKFLOW,
        OCI_WORKFLOW,
        CODEQL_WORKFLOW,
        DEPENDENCY_REVIEW_WORKFLOW,
        SECURITY_WORKFLOW,
        PROVENANCE_WORKFLOW,
        RESILIENCE_WORKFLOW,
    ]

    evidence_hashes = {
        path.relative_to(ROOT).as_posix(): sha256_file(path) for path in CONTROLLED_EVIDENCE_PATHS
    }

    return {
        "schema_version": 1,
        "package": "part_x_computational_assurance_report_support",
        "model": MODEL,
        "source_release": SOURCE_RELEASE,
        "architecture": {
            "public_package": "src/hilmarbench",
            "public_modules": public_modules,
            "python_requirement": pyproject["project"]["requires-python"],
        },
        "automated_quality": {
            "pytest_items_collected": test_count,
            "branch_coverage_required": "--cov-branch" in addopts,
            "coverage_fail_under_percent": coverage_threshold,
            "warnings_as_errors": "error" in pytest_config.get("filterwarnings", []),
            "pyright_mode": pyright["typeCheckingMode"],
            "ruff_target_version": ruff["target-version"],
            "ruff_configured": True,
        },
        "environment_matrix": parse_python_matrix(),
        "deterministic_environment": {
            "timezone": "UTC",
            "python_hash_seed": "0",
            "omp_num_threads": "1",
            "openblas_num_threads": "1",
            "mkl_num_threads": "1",
            "numexpr_num_threads": "1",
        },
        "workflow_inventory": [path.relative_to(ROOT).as_posix() for path in workflow_paths],
        "release_assurance": {
            "exact_constraints": "requirements/constraints-py313.txt",
            "oci_reproduction": True,
            "cyclonedx_sbom": True,
            "spdx_sbom": True,
            "github_oidc_attestation": True,
            "digest_addressed_oci_image": True,
            "codeql": True,
            "dependency_review": True,
            "dependency_audit": True,
            "repository_backup_restore": True,
        },
        "independent_accounting_recalculation": {
            "implementation_boundary": independent["implementation_boundary"],
            "official_equity_maximum_absolute_difference": reconciliation[
                "official_equity_maximum_absolute_difference"
            ],
            "official_return_maximum_absolute_difference": reconciliation[
                "official_return_maximum_absolute_difference"
            ],
            "maximum_aggregate_absolute_differences": reconciliation[
                "maximum_aggregate_absolute_differences"
            ],
            "position_alignment": reconciliation["position_alignment"],
            "source_release": independent["release"],
        },
        "evidence_classes": {
            "public_benchmarks": "code-reproducible",
            "nostra_aggregated_results": "artifact-verified",
            "private_detailed_evidence": "private-controlled",
            "external_independent_validation": "not_claimed",
        },
        "governance": {
            "change_control_documented": True,
            "proprietary_boundary_documented": True,
            "release_evidence_architecture_documented": True,
        },
        "controlled_evidence_sha256": evidence_hashes,
        "limitations": [
            (
                "Le recalcul autonome porte sur le noyau comptable et ne "
                "constitue pas une reproduction publique de la logique "
                "propriétaire de Nostra AI."
            ),
            (
                "L'indépendance d'implémentation du recalcul comptable ne "
                "constitue pas une validation externe indépendante."
            ),
            (
                "Une couverture de code complète démontre l'exécution des "
                "chemins mesurés, non l'exhaustivité des hypothèses économiques."
            ),
            (
                "Les SBOM, manifestes, empreintes et attestations établissent "
                "la provenance et l'intégrité des artefacts ; ils ne démontrent "
                "pas la validité économique future du modèle."
            ),
            (
                "La reproductibilité publique de Nostra AI reste limitée par "
                "la frontière propriétaire explicitement documentée."
            ),
        ],
    }


def scientific(value: float) -> str:
    return f"{value:.3e}"


def write_markdown(summary: dict[str, Any]) -> None:
    quality = summary["automated_quality"]
    matrix = summary["environment_matrix"]
    recalc = summary["independent_accounting_recalculation"]
    differences = recalc["maximum_aggregate_absolute_differences"]

    lines = [
        "# Partie X - Assurance computationnelle",
        "",
        "## Tableau 10.1",
        "",
        "### Contrôles automatisés et environnement",
        "",
        "| Élément | Résultat contrôlé |",
        "|---|---|",
        f"| Tests pytest collectés | {quality['pytest_items_collected']} |",
        (
            "| Couverture de branches exigée | "
            f"{'Oui' if quality['branch_coverage_required'] else 'Non'} |"
        ),
        (f"| Seuil minimal de couverture | {quality['coverage_fail_under_percent']} % |"),
        f"| Pyright | {quality['pyright_mode']} |",
        f"| Ruff | Cible {quality['ruff_target_version']} |",
        ("| Versions Python CI | " + ", ".join(matrix["python_versions"]) + " |"),
        ("| Systèmes CI | " + ", ".join(matrix["operating_systems"]) + " |"),
        f"| Environnement canonique | Python {matrix['canonical_python']} |",
        "",
        "## Tableau 10.2",
        "",
        "### Recalcul indépendant du noyau comptable",
        "",
        "| Mesure | Écart absolu maximal |",
        "|---|---:|",
        (
            "| Rendement officiel | "
            + scientific(recalc["official_return_maximum_absolute_difference"])
            + " |"
        ),
        (
            "| Equity officielle | "
            + scientific(recalc["official_equity_maximum_absolute_difference"])
            + " |"
        ),
    ]

    labels = {
        "final_equity": "Capital final",
        "cagr": "CAGR",
        "annualized_volatility": "Volatilité annualisée",
        "sharpe": "Ratio de Sharpe",
        "maximum_drawdown": "Perte maximale",
        "turnover_total": "Rotation cumulée",
    }

    for key in labels:
        lines.append(f"| {labels[key]} | {scientific(float(differences[key]))} |")

    lines.extend(
        [
            "",
            (
                "Le recalcul est réalisé par une implémentation autonome "
                "n'important aucune fonction de `src/hilmarbench`."
            ),
            "",
            (
                "Cette indépendance porte sur l'implémentation comptable. "
                "Elle ne constitue ni une validation externe indépendante "
                "de Nostra AI, ni une reproduction publique de la logique "
                "propriétaire du modèle."
            ),
            "",
            "## Tableau 10.3",
            "",
            "### Chaîne logicielle et release",
            "",
            "| Contrôle | Présence dans l'architecture |",
            "|---|---|",
            "| Contraintes exactes Python | Oui |",
            "| Reproduction OCI | Oui |",
            "| SBOM CycloneDX | Oui |",
            "| SBOM SPDX | Oui |",
            "| Attestation GitHub OIDC | Oui |",
            "| CodeQL | Oui |",
            "| Dependency review | Oui |",
            "| Audit des dépendances | Oui |",
            "| Sauvegarde et restauration du dépôt | Oui |",
            "",
            "## Classes de preuve",
            "",
            "| Élément | Classe |",
            "|---|---|",
            "| Benchmarks publics | `code-reproducible` |",
            "| Résultats agrégés Nostra AI | `artifact-verified` |",
            "| Preuves détaillées privées | `private-controlled` |",
            "| Validation externe indépendante | Non revendiquée |",
            "",
            "## Limites",
            "",
        ]
    )

    for limitation in summary["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            (
                "Conclusion contrôlée : l'architecture publique fournit une "
                "assurance computationnelle substantielle sur le noyau "
                "comptable, les contrôles automatisés, la reproductibilité "
                "des composants publics, la provenance, la sécurité de la "
                "chaîne logicielle et l'intégrité des artefacts. Cette "
                "assurance ne doit pas être confondue avec une validation "
                "externe indépendante de Nostra AI ni avec une garantie de "
                "validité économique future."
            ),
            "",
        ]
    )

    TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TABLE_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_manifest_and_checksums() -> None:
    controlled_paths = [
        SUMMARY_PATH,
        TABLE_PATH,
        GENERATOR_PATH,
        TEST_PATH,
        *CONTROLLED_EVIDENCE_PATHS,
    ]

    unique_paths = sorted(
        set(controlled_paths),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )

    records = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for path in unique_paths
    ]

    write_json(
        MANIFEST_PATH,
        {
            "schema_version": 1,
            "package": "part_x_computational_assurance_report_support",
            "model": MODEL,
            "source_release": SOURCE_RELEASE,
            "files": records,
        },
    )

    CHECKSUMS_PATH.write_text(
        "".join(f"{record['sha256']}  {record['path']}\n" for record in records),
        encoding="utf-8",
    )


def main() -> None:
    SUPPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_count = collect_pytest_items()
    summary = build_summary(
        test_count=test_count,
    )

    write_json(
        SUMMARY_PATH,
        summary,
    )
    write_markdown(summary)
    write_manifest_and_checksums()

    print("PASS_PART_X_COMPUTATIONAL_ASSURANCE_SUPPORT_READY")
    print(f"Tests collectés : {test_count}")
    print(f"Résumé : {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Tableau : {TABLE_PATH.relative_to(ROOT)}")
    print(f"Manifeste : {MANIFEST_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
