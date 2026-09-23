# Signal Schema Reference

This document is the authoritative field reference for the canonical
`Signal` model and the aggregate structures. It complements the narrative in
the top-level `README.md`.

## Signal

| Field | Type | Meaning |
|-------|------|---------|
| `signal_id` | string | Deterministic id `sig_<hash>` derived from run, name, timestamp and ordinal. |
| `run_id` | string | The workflow run a signal belongs to. |
| `kind` | enum | One of `invocation`, `tool`, `retrieval`, `evaluation`, `error`, `lifecycle`. |
| `name` | string | Human-facing step name (node, tool or operation). |
| `ts` | integer | Epoch milliseconds, coerced from any source time format. |
| `duration_ms` | integer | Wall-clock duration of the step. |
| `severity` | enum | One of `ok`, `notice`, `warn`, `error`, `critical`. |
| `quality` | float or null | Normalized 0..1 quality score when scored. |
| `tokens_in` | integer | Prompt / input token count. |
| `tokens_out` | integer | Completion / output token count. |
| `source` | string | Detected vendor family. |
| `attributes` | object | Passthrough of vendor-specific fields. |

## RunSummary

| Field | Type | Meaning |
|-------|------|---------|
| `run_id` | string | Run identifier. |
| `signal_count` | integer | Number of signals in the run. |
| `kind_counts` | object | Count of signals per kind. |
| `span_ms` | integer | Time between first and last signal. |
| `total_duration_ms` | integer | Sum of signal durations. |
| `tokens_in` / `tokens_out` | integer | Token totals. |
| `quality_mean` / `quality_min` | float or null | Aggregated quality over scored signals. |
| `scored_signals` | integer | How many signals carried a quality score. |
| `error_count` | integer | Error-kind or error/critical-severity signals. |
| `severity_load` | integer | Summed severity weights. |
| `reliability` | float | 0..100 reliability score. |
| `p50_duration_ms` / `p95_duration_ms` | integer | Duration percentiles. |
| `sources` | array | Distinct source families present in the run. |

## RunGroup

| Field | Type | Meaning |
|-------|------|---------|
| `run_count` | integer | Number of runs. |
| `signal_count` | integer | Total signals across runs. |
| `total_tokens_in` / `total_tokens_out` | integer | Fabric token totals. |
| `fabric_reliability` | float | Mean of per-run reliability. |
| `fabric_quality_mean` | float or null | Mean quality across all scored signals. |
| `runs` | array | List of `RunSummary` objects, sorted by `run_id`. |
