import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from signalweave.cli import _parse_events  # noqa: E402


class ParseEventsTests(unittest.TestCase):
    def test_blank_input(self):
        self.assertEqual(_parse_events("   "), [])

    def test_array_and_jsonl_agree(self):
        arr = _parse_events('[{"a": 1}, {"a": 2}]')
        lines = _parse_events('{"a": 1}\n{"a": 2}\n')
        self.assertEqual(arr, lines)

    def test_non_object_line_is_rejected(self):
        with self.assertRaises(ValueError):
            _parse_events("[1, 2]")
        with self.assertRaises(ValueError):
            _parse_events('{"a": 1}\nnot json')


if __name__ == "__main__":
    unittest.main()
