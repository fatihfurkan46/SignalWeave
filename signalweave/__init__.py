"""SignalWeave — an AI workflow telemetry fabric.

SignalWeave normalizes heterogeneous framework events into a common signal
model, aggregates quality and reliability indicators, groups runs and emits
portable, deterministic summaries.
"""

from .model import Signal, SignalKind, Severity
from .normalize import normalize_event, normalize_stream
from .aggregate import aggregate, RunGroup, RunSummary
from .report import render_report

__all__ = [
    "Signal",
    "SignalKind",
    "Severity",
    "normalize_event",
    "normalize_stream",
    "aggregate",
    "RunGroup",
    "RunSummary",
    "render_report",
    "__version__",
]

__version__ = "0.4.0"
