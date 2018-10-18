"""SignalWeave — an AI workflow telemetry fabric.

SignalWeave normalizes heterogeneous framework events into a common signal
model, aggregates quality and reliability indicators, groups runs and emits
portable, deterministic summaries.
"""

from .model import Signal, SignalKind, Severity
