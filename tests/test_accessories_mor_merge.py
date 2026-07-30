"""MOR loads all three vendor ranges, not just the newest file.

Regression guard: _load_extra_family used to return only the most-recently-
modified file matching "Manual Override". The 2026-07-29 Shakti drop
(_R1_Updated, 13 MRS* rows) would therefore have silently replaced the 23
Q-Tork/Transtork rows in _R1 — with a log line that read like success.
The three ranges are disjoint and all three are live products.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from accessories import load_accessories  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


class TestMorMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [
            r for r in load_accessories(DATA)["rows"] if r["family"] == "MOR"
        ]

    def test_all_three_vendor_ranges_load(self):
        self.assertEqual(len(self.rows), 36)

    def test_each_vendor_prefix_present_in_full(self):
        codes = [r["code"] for r in self.rows]
        for prefix, expected in (("MRQ", 13), ("MRT", 10), ("MRS", 13)):
            found = sum(1 for c in codes if c.startswith(prefix))
            self.assertEqual(found, expected, f"{prefix}: {found} != {expected}")

    def test_codes_are_unique(self):
        codes = [r["code"] for r in self.rows]
        self.assertEqual(len(codes), len(set(codes)))

    def test_family_count_reflects_merge(self):
        fams = {f["key"]: f for f in load_accessories(DATA)["families"]}
        self.assertEqual(fams["MOR"]["count"], 36)


if __name__ == "__main__":
    unittest.main()
