"""Report rendering: portable, deterministic summaries.

Two output formats are supported:

* ``json`` — the machine-readable :class:`~signalweave.aggregate.RunGroup`
  serialized with sorted keys and stable separators.
* ``text`` — a fixed-width, human-readable weave report with a header banner,
  per-run rows and a fabric footer.

Both formats are pure functions of the input aggregate, so byte-for-byte
reproducibility holds across machines.
"""

from __future__ import annotations

import json
from typing import List

from .aggregate import RunGroup, RunSummary


def _bar(value: float, width: int = 20) -> str:
    """Render a 0..100 value as an ASCII meter."""

    filled = int(round((value / 100.0) * width))
    filled = max(0, min(width, filled))
    return "#" * filled + "-" * (width - filled)


def _fmt_quality(value) -> str:
    return f"{value:.3f}" if value is not None else "  -  "


def _render_text(group: RunGroup) -> str:
    lines: List[str] = []
    lines.append("=" * 64)
    lines.append("  SIGNALWEAVE  ·  AI WORKFLOW TELEMETRY FABRIC")
    lines.append("=" * 64)
    lines.append("")
    lines.append(
        f"  runs={group.run_count}  signals={group.signal_count}  "
        f"tokens_in={group.total_tokens_in}  tokens_out={group.total_tokens_out}"
    )
    lines.append(
        f"  fabric_reliability={group.fabric_reliability:6.2f}  "
        f"[{_bar(group.fabric_reliability)}]"
    )
    q = group.fabric_quality_mean
    lines.append(f"  fabric_quality   ={_fmt_quality(q)}")
    lines.append("-" * 64)
    lines.append(
        f"  {'RUN':<18} {'SIG':>4} {'ERR':>4} {'REL':>7} {'QUAL':>6} "
        f"{'P50':>6} {'P95':>6}"
    )
    lines.append("-" * 64)

    for run in group.runs:
        lines.append(
            f"  {_clip(run.run_id, 18):<18} {run.signal_count:>4} "
            f"{run.error_count:>4} {run.reliability:>7.2f} "
            f"{_fmt_quality(run.quality_mean):>6} "
            f"{run.p50_duration_ms:>6} {run.p95_duration_ms:>6}"
        )

    lines.append("-" * 64)
    lines.append("  kind distribution (fabric):")
    dist = _kind_distribution(group.runs)
    for kind in sorted(dist):
        lines.append(f"    {kind:<14} {dist[kind]:>5}")
    lines.append("=" * 64)
    return "\n".join(lines) + "\n"


def _clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "\u2026"


