
#!/usr/bin/env bash

run_control() {
  control_name="$1"
  shift

  echo
  echo "=== $control_name ==="

  "$@"
  control_rc=$?

  if [ "$control_rc" -ne 0 ]; then
    echo "ÉCHEC : $control_name"
    exit "$control_rc"
  fi
}

export PYTHONPATH=src
export TZ=UTC
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

run_control \
  "Ruff check" \
  python -m ruff check .

run_control \
  "Ruff format" \
  python -m ruff format --check .

run_control \
  "Pyright" \
  python -m pyright

run_control \
  "Tests et couverture" \
  python -m pytest

run_control \
  "Audit du dépôt public" \
  python tools/audit_public_repository.py

run_control \
  "Audit artifacts/latest" \
  python tools/audit_public_release.py \
    --root artifacts/latest \
    --release

run_control \
  "Audit artifacts/releases/v0.2.0" \
  python tools/audit_public_release.py \
    --root artifacts/releases/v0.2.0 \
    --release

run_control \
  "Audit artifacts/releases/v0.2.1" \
  python tools/audit_public_release.py \
    --root artifacts/releases/v0.2.1 \
    --release

run_control \
  "Reproduction canonique" \
  python tools/reproduce_reference_release.py \
    --release-dir artifacts/releases/v0.2.1

run_control \
  "Hashes artifacts/latest" \
  python tools/verify_release_hashes.py \
    artifacts/latest

run_control \
  "Hashes v0.2.1" \
  python tools/verify_release_hashes.py \
    artifacts/releases/v0.2.1

run_control \
  "Rapport environnement numérique" \
  python tools/numeric_environment_report.py

echo
echo "OCI INSTITUTIONAL REPRODUCTION PASSED"
