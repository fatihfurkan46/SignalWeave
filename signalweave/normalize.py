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
        "name": event.get("graph_node") or event.get("node_id") or "node",
        "ts": event.get("emitted_at") or event.get("ts"),
        "duration_ms": event.get("elapsed_ms", 0),
        "severity": event.get("state"),
        "quality": event.get("confidence"),
        "tokens_in": event.get("tokens", {}).get("in", 0) if isinstance(event.get("tokens"), dict) else 0,
        "tokens_out": event.get("tokens", {}).get("out", 0) if isinstance(event.get("tokens"), dict) else 0,
        "attributes": {k: v for k, v in event.items() if k not in _GRAPH_KNOWN},
    }


def _adapter_agentkit(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": event.get("run_id") or "run-unknown",
        "kind": event.get("invocation_type") or "tool",
        "name": event.get("tool_name") or event.get("name") or "tool",
        "ts": event.get("timestamp") or event.get("ts"),
        "duration_ms": event.get("duration_ms", 0),
        "severity": event.get("outcome"),
        "quality": event.get("score"),
        "tokens_in": event.get("input_tokens", 0),
        "tokens_out": event.get("output_tokens", 0),
        "attributes": event.get("meta", {}) or {},
    }


def _adapter_generic(event: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": event.get("run_id") or event.get("run") or "run-unknown",
        "kind": event.get("kind") or event.get("type") or "invocation",
        "name": event.get("name") or event.get("event") or "event",
        "ts": event.get("ts") or event.get("timestamp") or event.get("time"),
        "duration_ms": event.get("duration_ms") or event.get("latency_ms") or 0,
        "severity": event.get("severity") or event.get("level") or event.get("status"),
        "quality": event.get("quality") or event.get("score"),
        "tokens_in": event.get("tokens_in", 0),
        "tokens_out": event.get("tokens_out", 0),
        "attributes": event.get("attributes", {}) or {},
    }


_GRAPH_KNOWN = {
    "session", "run_id", "category", "graph_node", "node_id",
    "emitted_at", "ts", "elapsed_ms", "state", "confidence", "tokens",
}

_ADAPTERS = {
    "otel": _adapter_otel,
    "langchain": _adapter_langchain,
    "graphflow": _adapter_graphflow,
    "agentkit": _adapter_agentkit,
    "generic": _adapter_generic,
}


def _duration(event: Dict[str, Any], attrs: Dict[str, Any]) -> int:
    if "duration_ms" in event:
        return int(event["duration_ms"] or 0)
    start = event.get("start_time")
    end = event.get("end_time")
    if start is not None and end is not None:
        return max(0, _as_int_ms(end) - _as_int_ms(start))
    return int(attrs.get("duration_ms", 0) or 0)


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_event(event: Dict[str, Any], ordinal: int = 0) -> Signal:
    """Project a single raw event dict onto a canonical :class:`Signal`."""

    source = _detect_source(event)
    adapter = _ADAPTERS.get(source, _adapter_generic)
    fields = adapter(event)

    run_id = str(fields["run_id"])
    name = str(fields["name"])
    ts = _as_int_ms(fields["ts"])
    kind = SignalKind.coerce(fields["kind"])
    severity = Severity.coerce(fields["severity"])

    return Signal(
        signal_id=make_signal_id(run_id, name, ts, ordinal),
        run_id=run_id,
        kind=kind,
        name=name,
        ts=ts,
        duration_ms=_coerce_int(fields.get("duration_ms")),
        severity=severity,
        quality=_as_float(fields.get("quality")),
        tokens_in=_coerce_int(fields.get("tokens_in")),
        tokens_out=_coerce_int(fields.get("tokens_out")),
        source=source,
        attributes=dict(fields.get("attributes") or {}),
    )


def normalize_stream(events: Iterable[Dict[str, Any]]) -> List[Signal]:
    """Normalize an iterable of raw events into a deterministically ordered list.

    Signals are sorted by ``(ts, run_id, name)`` so identical input always
    yields identical output regardless of arrival order.
    """

    signals = [normalize_event(ev, ordinal=i) for i, ev in enumerate(events)]
    signals.sort(key=lambda s: (s.ts, s.run_id, s.name, s.signal_id))
    return signals
