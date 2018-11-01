"""Aggregation: group normalized signals into runs and compute indicators.

The aggregator is pure and deterministic. Given the same list of signals it
always produces byte-identical summaries. It computes three families of
indicators per run:

* **Volume** — signal counts by kind, token totals, wall-clock span.
* **Quality** — mean / min quality across scored signals.
* **Reliability** — a 0..100 score derived from severity weights, blended with
  a latency-stability term.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model import Signal, SignalKind, Severity


@dataclass
class RunSummary:
    """Aggregated indicators for a single run."""

    run_id: str
    signal_count: int
    kind_counts: Dict[str, int]
    span_ms: int
    total_duration_ms: int
    tokens_in: int
    tokens_out: int
    quality_mean: Optional[float]
    quality_min: Optional[float]
    scored_signals: int
    error_count: int
    severity_load: int
