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
