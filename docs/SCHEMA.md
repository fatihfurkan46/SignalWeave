# Signal Schema Reference

This document is the authoritative field reference for the canonical
`Signal` model and the aggregate structures. It complements the narrative in
the top-level `README.md`.

## Signal

| Field | Type | Meaning |
|-------|------|---------|
| `signal_id` | string | Deterministic id `sig_<hash>` derived from run, name, timestamp and ordinal. |
| `run_id` | string | The workflow run a signal belongs to. |
