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
        return []
    if stripped[0] == "[":
        data = json.loads(stripped)
        if not isinstance(data, list):
            raise ValueError("top-level JSON must be an array of event objects")
        return [dict(item) for item in data]
    # JSONL
    events: List[Dict[str, Any]] = []
    for lineno, line in enumerate(stripped.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {lineno}: invalid JSON ({exc.msg})") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"line {lineno}: expected an object")
        events.append(obj)
    return events


def _emit(out: TextIO, payload: str) -> None:
    out.write(payload)
    if not payload.endswith("\n"):
        out.write("\n")


def _cmd_normalize(args: argparse.Namespace) -> int:
    events = _parse_events(_read_text(args.input))
    signals = normalize_stream(events)
    lines = [json.dumps(s.to_dict(), sort_keys=True, separators=(",", ":")) for s in signals]
    _emit(sys.stdout, "\n".join(lines))
    return 0


def _cmd_aggregate(args: argparse.Namespace) -> int:
    events = _parse_events(_read_text(args.input))
    group = aggregate(normalize_stream(events))
    _emit(sys.stdout, json.dumps(group.to_dict(), sort_keys=True, indent=2))
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    events = _parse_events(_read_text(args.input))
    group = aggregate(normalize_stream(events))
    _emit(sys.stdout, render_report(group, fmt=args.format))
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    events = _parse_events(_read_text(args.input))
    signals = [s for s in normalize_stream(events) if s.run_id == args.run_id]
    if not signals:
        sys.stderr.write(f"no signals found for run_id={args.run_id!r}\n")
        return 2
    payload = {
        "run_id": args.run_id,
        "signal_count": len(signals),
        "signals": [s.to_dict() for s in signals],
    }
    _emit(sys.stdout, json.dumps(payload, sort_keys=True, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signalweave",
        description="AI workflow telemetry fabric — normalize, aggregate, report.",
    )
    parser.add_argument("--version", action="version", version=f"signalweave {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_input(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "input",
            nargs="?",
            default="-",
