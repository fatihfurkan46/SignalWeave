import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signalweave.aggregate import _reliability  # noqa: E402


def signal(duration_ms, weight=0):
    return SimpleNamespace(duration_ms=duration_ms, severity=SimpleNamespace(weight=weight))


class ReliabilityEdgeTests(unittest.TestCase):
    def test_no_signals_is_full_score(self):
        self.assertEqual(_reliability([]), 100.0)

    def test_zero_durations_do_not_divide_by_zero(self):
        self.assertEqual(_reliability([signal(0), signal(0)]), 100.0)

    def test_score_is_clamped(self):
        value = _reliability([signal(0, weight=9) for _ in range(5)])
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 100.0)


if __name__ == "__main__":
    unittest.main()
