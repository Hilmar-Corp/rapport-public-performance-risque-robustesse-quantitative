PYTHON ?= python3
RELEASE ?= artifacts/latest
VERSIONED_RELEASE ?= artifacts/releases/v0.2.0
CONSTRAINTS ?= requirements/constraints-py313.txt

.PHONY: install format lint test audit reproduce security institutional-check

install:
	$(PYTHON) -m pip install -e ".[dev,hmm]"

format:
	$(PYTHON) -m ruff format
	$(PYTHON) -m ruff check --fix

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

test:
	PYTHONPATH=src $(PYTHON) -m pytest

audit:
	PYTHONPATH=src $(PYTHON) tools/audit_public_repository.py
	PYTHONPATH=src $(PYTHON) tools/audit_public_release.py --root $(RELEASE) --release
	PYTHONPATH=src $(PYTHON) tools/audit_public_release.py --root $(VERSIONED_RELEASE) --release
	$(PYTHON) tools/finalize_publication_architecture.py audit-release --root $(RELEASE)
	$(PYTHON) tools/finalize_publication_architecture.py audit-release --root $(VERSIONED_RELEASE)

reproduce:
	PYTHONPATH=src $(PYTHON) tools/reproduce_reference_release.py --release-dir $(RELEASE)

security:
	pip-audit -r $(CONSTRAINTS) --strict --progress-spinner off

institutional-check: lint test audit reproduce
