"""The common signal model.

Every framework event, regardless of vendor shape, is projected onto a single
canonical :class:`Signal`. Downstream aggregation and reporting operate only on
this normalized form, which keeps the fabric vendor-agnostic.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


class SignalKind(str, enum.Enum):
    """Canonical categories a raw event can be projected onto."""

    INVOCATION = "invocation"      # a model / tool / chain call
    TOOL = "tool"                  # a tool or function execution
    RETRIEVAL = "retrieval"        # a vector / document lookup
    EVALUATION = "evaluation"      # a scored quality check
    ERROR = "error"                # a failure or exception
    LIFECYCLE = "lifecycle"        # run start / end / checkpoint

    @classmethod
    def coerce(cls, value: Any) -> "SignalKind":
        if isinstance(value, SignalKind):
            return value
        text = str(value or "").strip().lower()
        for member in cls:
            if member.value == text:
                return member
        # Heuristic mapping for common vendor vocabularies.
        alias = {
            "llm": cls.INVOCATION,
            "chat": cls.INVOCATION,
            "completion": cls.INVOCATION,
            "generation": cls.INVOCATION,
            "function": cls.TOOL,
            "action": cls.TOOL,
            "search": cls.RETRIEVAL,
            "lookup": cls.RETRIEVAL,
            "score": cls.EVALUATION,
            "eval": cls.EVALUATION,
            "exception": cls.ERROR,
            "fault": cls.ERROR,
            "span": cls.LIFECYCLE,
            "trace": cls.LIFECYCLE,
        }
        return alias.get(text, cls.INVOCATION)


class Severity(str, enum.Enum):
    """Ordered severity ladder used for reliability scoring."""

    OK = "ok"
    NOTICE = "notice"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        return {"ok": 0, "notice": 1, "warn": 3, "error": 7, "critical": 12}[self.value]

    @classmethod
    def coerce(cls, value: Any) -> "Severity":
        if isinstance(value, Severity):
            return value
        text = str(value or "ok").strip().lower()
        for member in cls:
            if member.value == text:
                return member
        alias = {
            "info": cls.NOTICE,
            "debug": cls.OK,
            "warning": cls.WARN,
            "err": cls.ERROR,
            "fatal": cls.CRITICAL,
            "success": cls.OK,
            "failure": cls.ERROR,
        }
        return alias.get(text, cls.OK)


@dataclass(frozen=True)
class Signal:
    """A single normalized telemetry point.

    Attributes are intentionally flat so the model serializes to compact,
    diff-friendly JSON. ``ts`` is an epoch-milliseconds integer to keep
    ordering deterministic across sources.
    """

    signal_id: str
    run_id: str
    kind: SignalKind
    name: str
    ts: int
    duration_ms: int = 0
    severity: Severity = Severity.OK
    quality: Optional[float] = None       # 0.0 .. 1.0 when known
    tokens_in: int = 0
    tokens_out: int = 0
    source: str = "unknown"
    attributes: Dict[str, Any] = field(default_factory=dict)
