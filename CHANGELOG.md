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

