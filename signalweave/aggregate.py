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
    reliability: float
    p50_duration_ms: int
    p95_duration_ms: int
    sources: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "run_id": self.run_id,
            "signal_count": self.signal_count,
            "kind_counts": self.kind_counts,
            "span_ms": self.span_ms,
            "total_duration_ms": self.total_duration_ms,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "quality_mean": self.quality_mean,
            "quality_min": self.quality_min,
            "scored_signals": self.scored_signals,
            "error_count": self.error_count,
            "severity_load": self.severity_load,
            "reliability": self.reliability,
            "p50_duration_ms": self.p50_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "sources": self.sources,
        }


@dataclass
class RunGroup:
    """A fabric-wide aggregate over every run."""

    run_count: int
    signal_count: int
    total_tokens_in: int
    total_tokens_out: int
    fabric_reliability: float
    fabric_quality_mean: Optional[float]
    runs: List[RunSummary] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "run_count": self.run_count,
            "signal_count": self.signal_count,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "fabric_reliability": self.fabric_reliability,
            "fabric_quality_mean": self.fabric_quality_mean,
            "runs": [r.to_dict() for r in self.runs],
        }


def _percentile(values: List[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = pct / 100.0 * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return int(round(ordered[low] + (ordered[high] - ordered[low]) * frac))


def _reliability(signals: List[Signal]) -> float:
    """Compute a 0..100 reliability score.

    The score starts at 100 and is reduced by the mean severity weight per
    signal (scaled) and by latency instability measured as the coefficient of
    variation of durations. The result is clamped and rounded to two decimals.
    """

    if not signals:
        return 100.0

    severity_load = sum(s.severity.weight for s in signals)
    severity_penalty = min(60.0, (severity_load / len(signals)) * 8.0)

    durations = [s.duration_ms for s in signals if s.duration_ms > 0]
    stability_penalty = 0.0
    if len(durations) >= 2:
        mean = statistics.fmean(durations)
        if mean > 0:
            cv = statistics.pstdev(durations) / mean
            stability_penalty = min(20.0, cv * 10.0)

    score = 100.0 - severity_penalty - stability_penalty
    return round(max(0.0, min(100.0, score)), 2)


def _summarize_run(run_id: str, signals: List[Signal]) -> RunSummary:
    kind_counts = Counter(s.kind.value for s in signals)
    timestamps = [s.ts for s in signals if s.ts > 0]
    span = (max(timestamps) - min(timestamps)) if len(timestamps) >= 2 else 0

    scored = [s.quality for s in signals if s.quality is not None]
    quality_mean = round(statistics.fmean(scored), 4) if scored else None
    quality_min = round(min(scored), 4) if scored else None

    durations = [s.duration_ms for s in signals]
    error_count = sum(
        1 for s in signals
        if s.kind == SignalKind.ERROR or s.severity in (Severity.ERROR, Severity.CRITICAL)
    )

    return RunSummary(
        run_id=run_id,
        signal_count=len(signals),
        kind_counts=dict(sorted(kind_counts.items())),
        span_ms=span,
        total_duration_ms=sum(durations),
        tokens_in=sum(s.tokens_in for s in signals),
        tokens_out=sum(s.tokens_out for s in signals),
        quality_mean=quality_mean,
        quality_min=quality_min,
