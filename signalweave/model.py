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


