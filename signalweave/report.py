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
