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

