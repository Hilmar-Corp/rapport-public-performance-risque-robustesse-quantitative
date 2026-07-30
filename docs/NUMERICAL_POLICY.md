# Numerical Computation and Validation Policy

## 1. Scope

This policy applies to all public quantitative calculations, benchmark
strategies, performance metrics, risk metrics, transaction-cost calculations,
release artifacts and reproduction controls contained in this repository.

It does not disclose or govern the proprietary decision logic of Nostra AI.

## 2. Canonical environment

The canonical numerical environment shall use:

- Python 3.13 for controlled release reproduction;
- UTC for all timestamps and calendar boundaries;
- UTF-8 encoding;
- deterministic random seeds where randomness is used;
- one computational thread for BLAS, OpenMP and numerical backends during
  canonical reproduction;
- the exact dependency constraints stored under `requirements/`;
- explicitly sorted observations before any time-series calculation.

## 3. Floating-point representation

Calculations use IEEE 754 double-precision floating-point values unless a
different representation is explicitly documented.

Published values must not rely on string formatting as a substitute for
numerical comparison.

Comparisons shall use explicit absolute and relative tolerances appropriate to
the metric under test.

Default tolerances:

- accounting identities: absolute tolerance `1e-12`;
- deterministic daily series: absolute tolerance `1e-12`;
- aggregate metrics: relative tolerance `1e-10`, absolute tolerance `1e-12`;
- cross-platform scientific-library comparisons: relative tolerance `1e-8`,
  absolute tolerance `1e-10`.

Any wider tolerance requires a documented justification.

## 4. Missing and invalid values

The following values are invalid in final published metrics and release
manifests:

- positive infinity;
- negative infinity;
- undefined division results;
- silent coercion failures;
- invalid timestamps.

NaN values are permitted only where a warm-up period or unavailable historical
input is explicitly defined by the methodology.

NaN values must never be silently converted to zero.

## 5. Time-series ordering

Every calculation must verify:

- monotonic chronological ordering;
- absence of duplicate canonical timestamps;
- explicit timezone handling;
- explicit execution lag;
- absence of future information in each decision.

Sorting data after a strategy decision has been calculated is prohibited.

## 6. Annualisation

Annualisation conventions must be explicit and consistent across code,
methodology and published artifacts.

Short true-live periods must not be presented using annualised performance
statistics unless the publication explicitly labels them as mechanically
annualised and unsuitable for inference.

## 7. Transaction costs

Transaction costs must be applied to the absolute change in the position
actually applied to returns.

The initial movement from cash into a position is part of turnover unless the
methodology explicitly states otherwise.

Costs must never be applied retrospectively using future positions.

## 8. Numerical regression

Critical published artifacts must be checked using:

- deterministic reproduction;
- SHA-256 manifests;
- metric-level numerical comparisons;
- accounting-identity tests;
- branch coverage;
- adversarial and property-based tests.

A change outside an approved tolerance is a release-blocking event.

## 9. Randomness

Any stochastic strategy or statistical procedure must record:

- the random seed;
- the library producing randomness;
- the library version;
- the number of threads;
- the walk-forward or resampling protocol.

Unseeded randomness is prohibited in controlled release production.

## 10. Exceptions

Any exception requires:

- written rationale;
- affected metric or artifact;
- quantified impact;
- approval in the change record;
- an expiry or remediation condition.
