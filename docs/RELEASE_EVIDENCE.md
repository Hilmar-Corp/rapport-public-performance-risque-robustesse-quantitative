
# Release Evidence Architecture

Each formal release links:

- a protected Git commit and tag;
- a digest-pinned Python base image;
- an OCI reproduction image published to GHCR;
- exact Python dependency constraints;
- CycloneDX and SPDX SBOMs;
- SHA-256 checksums;
- a provenance manifest;
- GitHub OIDC build attestations;
- controlled quantitative artifacts.

## Quantitative Control Evidence

The repository includes a public matrix covering 23 quantitative controls
and a separate registry of SHA-256 commitments to reconciled private
evidence.

The public registry contains no private path, model feature, coefficient,
threshold, daily position, daily return or execution trace. The commitments
support evidence integrity and later reconciliation; they do not make the
private evidence publicly reproducible and do not constitute independent
external model validation.

See:

- `governance/quantitative_validation_control_matrix.csv`;
- `governance/quantitative_evidence_commitments.csv`;
- `docs/QUANTITATIVE_VALIDATION_ROADMAP.md`.

Nostra AI remains `artifact-verified`. Its proprietary logic and execution
trace are not included.

The package supports due diligence, sandbox evaluation and controlled pilot
review. It does not constitute independent external model validation.
