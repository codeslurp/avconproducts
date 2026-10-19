"""2030F/2060F/2090F _Updated (2026-10-18) overwrite pressure slots 100-110.

Electric lives in source cols 59-60 (not 58). Linear (58) and Manual (61)
are empty in this drop. 2070F was not updated and keeps the old alt map.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import find_catalog_file, Catalog, BALL_VALVE  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


class TestBallSeriesUpdated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = find_catalog_file(DATA, BALL_VALVE.file_substring, BALL_VALVE.path_contains)
        cls.cat = Catalog(BALL_VALVE, path, DATA)
        cls.by_code = {str(r.get("c1")): r for r in cls.cat.rows}

    def test_updated_2030f_file_is_the_newest_match(self):
        src = find_catalog_file(DATA, "2030F BV NEW CODEING")
        self.assertIn("_Updated", src.name)

    def test_2030fc0001_fsc_4bar_is_a_real_model(self):
        row = self.by_code["2030FC0001"]
        self.assertEqual(str(row.get("c104")), "ACT-063SR07")

    def test_2030fc0001_electric_landed_on_109_not_linear_slot(self):
        row = self.by_code["2030FC0001"]
        self.assertEqual(str(row.get("c109")), "EA-21/D")
        self.assertIn(row.get("c122"), (None, ""))

    def test_2030fc0001_da_4bar_and_55bar_filled(self):
        row = self.by_code["2030FC0001"]
        self.assertEqual(str(row.get("c101")), "ACT-050D")
        self.assertEqual(str(row.get("c102")), "ACT-050D")

    def test_2070f_still_uses_the_unupdated_file(self):
        src = find_catalog_file(DATA, "2070F BV NEW CODEING")
        self.assertNotIn("_Updated", src.name)


if __name__ == "__main__":
    unittest.main()
