
ARG PYTHON_BASE=python:3.13.0-slim-bookworm@sha256:0de818129b26ed8f46fd772f540c80e277b67a28229531a1ba0fdacfaed19bcb
FROM ${PYTHON_BASE}

ARG PIP_VERSION=26.2
ARG SETUPTOOLS_VERSION=83.0.0
ARG WHEEL_VERSION=0.47.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0 \
    PYTHONPATH=/workspace/src \
    TZ=UTC \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY . /workspace

RUN python -m pip install \
      --no-cache-dir \
      "pip==${PIP_VERSION}" \
      "setuptools==${SETUPTOOLS_VERSION}" \
      "wheel==${WHEEL_VERSION}" \
    && python -m pip install \
      --no-cache-dir \
      --no-build-isolation \
      -c requirements/constraints-py313.txt \
      -e ".[dev,hmm]"

CMD ["bash", "scripts/reproduce_in_oci.sh"]
