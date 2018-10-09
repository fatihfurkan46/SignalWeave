"""Command-line interface for SignalWeave.

Commands
--------
``normalize``   Read raw events (JSON array or JSONL), emit canonical signals.
``aggregate``   Normalize then group into runs and emit the aggregate JSON.
``report``      Full pipeline: normalize -> aggregate -> render text/JSON.
``inspect``     Describe a single run's signals in detail.

All commands read from a path or ``-`` (stdin) and write to stdout, making the
tool composable in shell pipelines.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Iterable, List, TextIO

from . import __version__
from .aggregate import aggregate
from .normalize import normalize_stream
from .report import render_report


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _parse_events(text: str) -> List[Dict[str, Any]]:
    """Accept either a JSON array of events or newline-delimited JSON."""

    stripped = text.strip()
    if not stripped:
