"""Normalization: project heterogeneous vendor events onto :class:`Signal`.

SignalWeave accepts events from multiple AI framework shapes. Each source has a
small adapter that maps its idiosyncratic field names onto the canonical model.
Unknown shapes fall through to a permissive generic adapter so no event is ever
dropped silently.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .model import Signal, SignalKind, Severity, make_signal_id


def _as_int_ms(value: Any, default: int = 0) -> int:
    """Coerce a timestamp-like value to epoch milliseconds."""

    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        # Heuristic: seconds -> ms if the magnitude looks like seconds.
        if value < 10_000_000_000:
            return int(value * 1000)
        return int(value)
    text = str(value).strip()
    if not text:
        return default
    # ISO-8601 with trailing Z or offset.
    try:
        import datetime as _dt

        cleaned = text.replace("Z", "+00:00")
        dt = _dt.datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        pass
    try:
        return int(float(text))
    except ValueError:
        return default


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN guard
        return None
    return max(0.0, min(1.0, f))


def _detect_source(event: Dict[str, Any]) -> str:
    if "source" in event:
        return str(event["source"])
    if "vendor" in event:
        return str(event["vendor"])
    # Structural fingerprints for known families.
    if "span_kind" in event or "otel" in event:
        return "otel"
    if "chain" in event or "lc_run_id" in event:
        return "langchain"
    if "graph_node" in event or "node_id" in event:
        return "graphflow"
    if "tool_name" in event and "invocation_type" in event:
        return "agentkit"
    return "generic"


def _adapter_otel(event: Dict[str, Any]) -> Dict[str, Any]:
    attrs = event.get("attributes", {}) or {}
    return {
        "run_id": event.get("trace_id") or attrs.get("trace_id") or "run-unknown",
        "kind": event.get("span_kind") or event.get("kind") or "span",
        "name": event.get("name") or attrs.get("operation") or "span",
        "ts": event.get("start_time") or event.get("ts"),
        "duration_ms": _duration(event, attrs),
        "severity": event.get("status") or attrs.get("status_code"),
        "quality": attrs.get("quality"),
        "tokens_in": attrs.get("tokens.input", 0),
        "tokens_out": attrs.get("tokens.output", 0),
        "attributes": attrs,
    }


def _adapter_langchain(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": event.get("lc_run_id") or event.get("run_id") or "run-unknown",
        "kind": event.get("event_type") or event.get("chain") or "chain",
        "name": event.get("name") or event.get("serialized_name") or "chain_step",
        "ts": event.get("time") or event.get("ts"),
        "duration_ms": event.get("latency_ms", 0),
        "severity": event.get("level"),
        "quality": event.get("feedback_score"),
        "tokens_in": event.get("prompt_tokens", 0),
        "tokens_out": event.get("completion_tokens", 0),
        "attributes": event.get("metadata", {}) or {},
    }


def _adapter_graphflow(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": event.get("session") or event.get("run_id") or "run-unknown",
        "kind": event.get("category") or "invocation",
