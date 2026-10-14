"""Solenoid Valve loads the newest revision, not an older export.

Unlike MOR — where separate files hold disjoint vendor ranges and must be
merged — the solenoid files are successive REVISIONS of one range:
"Solenoid Valve_Updated6.xlsx" (2026-10-14) supersedes _Updated5. So plain
newest-wins is correct here and `merge_all` must NOT be set: merging would
also drag in "Solenoid Valve as accessories.xlsx", a differently-shaped
predecessor.

Note the row/code asymmetry: 101 rows but 100 distinct codes. SR432A3RWK02 is
used for two genuinely different products (BSP vs NPT end connection). That
defect predates this drop and is recorded in
docs/engineering-followups/2026-10-14-solenoid-valve-updated6.md.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from accessories import load_accessories  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"

# Codes that must be present in the live revision. Older codes stay listed so
# a silent rollback to an earlier file would still fail the new-code assertions.
NEW_CODES = [
    # added by the 2026-07-29 revision (S472S3RWK01 recoded away in _Updated6)
    "S331S3RWK01", "S350C3RWK01",
    "SR370S3SWK02", "SR485A2SWK01", "SR485A2SWN01", "SR485A2SWR01",
    # added by _Updated3 (2026-08-02)
    "S9350B4SWK01",
    # added by _Updated4 (2026-09-12)
    "SR384A3RWK01", "SR384A7SWK02", "SR484A3RWK01",
    "SR484A3RWR01", "SR484A3RWR02", "SR484A3RWR03", "SR484A3RFR03",
    "S9360A4SWR01", "S350C3RWK02", "S472S3RWK02", "S331S3RWK02",
    "SR487A2SEK01", "SR461A2SWR01", "SR123C3SWK01", "SR123C3SWK02",
    # added by _Updated5 (2026-09-25)
    "SR484A3RWR04", "SR484A3RFK01", "SR327C0RFK01",
    "S9210B4SWK01", "S9210B4SWK02", "S9230C5SWK01", "S9230C5SWK02",
    # added / recoded by _Updated6 (2026-10-14)
    "S9321S3RFK01", "S9321S3RFK02", "S9321S3RFR02", "S9321S3RFN02",
    "S9322S3RFK02", "S9322S3RFR02", "S9322S3RFN02",
    "S9322S3SWK05", "S9321S3SWK05", "S9322S3SWR05", "S9321S3SWR05",
    "S9322S3SWN02", "S9321S3SWN02",
    "S9350B4SWR01", "SR472S3RWK01", "SR472S3RFK01",
    "S9440C4SWR01", "S9442C4SWK01",
]

GONE_C3 = [
    "S9321C3RFK02", "S9321C3RFR02", "S9321C3RFN02",
    "S9322C3RFK02", "S9322C3RFR02", "S9322C3RFN02",
    "S9322C3SWK05", "S9321C3SWK05", "S9322C3SWR05", "S9321C3SWR05",
    "S9322C3SWN02", "S9321C3SWN02",
]


class TestSolenoidRevision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loaded = load_accessories(DATA)
        cls.rows = [r for r in loaded["rows"] if r["family"] == "Solenoid Valve"]
        cls.loaded = loaded
        cls.codes = {r["code"] for r in cls.rows}

    def test_loads_the_newest_revision(self):
        self.assertEqual(len(self.rows), 101)

    def test_all_new_codes_present(self):
        for code in NEW_CODES:
            self.assertIn(code, self.codes)

    def test_r487_was_recoded_to_sr487(self):
        self.assertNotIn("R487A2SEK01", self.codes)
        self.assertIn("SR487A2SEK01", self.codes)

    def test_s472_was_recoded_to_sr472(self):
        self.assertNotIn("S472S3RWK01", self.codes)
        self.assertIn("SR472S3RWK01", self.codes)

    def test_c3_9321_9322_recoded_to_s3(self):
        for code in GONE_C3:
            self.assertNotIn(code, self.codes)

    def test_distinct_code_count(self):
        codes = [r["code"] for r in self.rows]
        self.assertEqual(len(set(codes)), 100)

    def test_family_count_matches_rows(self):
        fams = {f["key"]: f for f in self.loaded["families"]}
        self.assertEqual(fams["Solenoid Valve"]["count"], 101)

    def test_source_is_updated6(self):
        self.assertIn("S9442C4SWK01", self.codes)


if __name__ == "__main__":
    unittest.main()
