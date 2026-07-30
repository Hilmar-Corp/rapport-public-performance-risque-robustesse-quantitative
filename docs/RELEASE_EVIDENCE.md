
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

Nostra AI remains `artifact-verified`. Its proprietary logic and execution
trace are not included.

The package supports due diligence, sandbox evaluation and controlled pilot
review. It does not constitute independent external model validation.
