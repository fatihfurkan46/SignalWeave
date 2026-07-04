# Changelog

All notable changes to SignalWeave are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-09-02

### Added
- Native C++17 aggregation core (`engine/signal_aggregate.cpp`) that consumes
  canonical JSONL signals and emits a matching run aggregate.
- `inspect` CLI command for dumping the full signal list of a single run.
- Fabric-wide reliability and quality means in both the text and JSON reports.
- Heterogeneous event fixtures covering LangChain, OpenTelemetry, GraphFlow,
  AgentKit and generic shapes.

### Changed
- Reliability scoring now blends a severity term with a latency-stability term
  derived from the coefficient of variation of durations.

## [0.3.0] - 2026-07-18

### Added
- Deterministic signal ordering keyed on `(ts, run_id, name, signal_id)`.
- Percentile (p50 / p95) duration columns in run summaries.

### Changed
- Timestamps normalized to epoch milliseconds across all adapters.

## [0.2.0] - 2026-05-30

### Added
- Source auto-detection with per-vendor adapters.
- Text weave report with ASCII reliability meters and kind distribution.

## [0.1.0] - 2026-04-12

### Added
- Initial signal model, generic normalizer, run aggregation and JSON report.
