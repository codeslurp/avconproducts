"""Solenoid Valve loads the 2026-07-29 revision (74 rows), not an older export.

Unlike MOR — where separate files hold disjoint vendor ranges and must be
merged — the solenoid files are successive REVISIONS of one range:
"Solenoid Valve_Updated3.xlsx" (2026-08-02) contains all 74 rows of its
predecessor plus 1 new code, with two coil-spec corrections. So plain
newest-wins is correct here and `merge_all` must NOT be set: merging would
also drag in "Solenoid Valve as accessories.xlsx", a differently-shaped
predecessor.

Note the row/code asymmetry: 75 rows but 74 distinct codes. SR432A3RWK02 is
used for two genuinely different products (BSP vs NPT end connection). That
defect predates this drop — it is present in _Updated2 too — and is recorded in
docs/engineering-followups/2026-07-29-2094f-trunnion-data-gaps.md.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from accessories import load_accessories  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"

# Added by the 2026-07-29 revision, absent from _Updated2.
NEW_CODES = [
    # added by the 2026-07-29 revision
    "R487A2SEK01", "S331S3RWK01", "S350C3RWK01", "S472S3RWK01",
    "SR370S3SWK02", "SR485A2SWK01", "SR485A2SWN01", "SR485A2SWR01",
    # added by _Updated3 (2026-08-02)
    "S9350B4SWK01",
]


class TestSolenoidRevision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [
            r for r in load_accessories(DATA)["rows"]
            if r["family"] == "Solenoid Valve"
        ]

    def test_loads_the_newest_revision(self):
        self.assertEqual(len(self.rows), 75)

    def test_all_new_codes_present(self):
        codes = {r["code"] for r in self.rows}
        for code in NEW_CODES:
            self.assertIn(code, codes)

    def test_distinct_code_count(self):
        # 74 distinct across 75 rows — see the SR432A3RWK02 note in the docstring.
        codes = [r["code"] for r in self.rows]
        self.assertEqual(len(set(codes)), 74)

    def test_family_count_matches_rows(self):
        fams = {f["key"]: f for f in load_accessories(DATA)["families"]}
        self.assertEqual(fams["Solenoid Valve"]["count"], 75)


if __name__ == "__main__":
    unittest.main()
