"""Gear Box (MHG) folds in the Shakti range dropped 2026-07-29.

The two sources are schema-identical (same 14 headers) and disjoint:
  Actuator/Manual Actuator/MHG Manual Gear Box ...  41 rows, MGT*, WGX-*
  Accessories/Gear Box Data for New Structure_R1   18 rows, MGS*, SE-*
The bare substring "Gear Box Data for New Structure" matches BOTH filenames, so
the ExtraRowSource must be pinned with path_contains="Accessories" — otherwise
it re-reads the master, adds nothing, and reports success.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import Catalog, find_catalog_file, MANUAL_GEARBOX  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


def _gearbox() -> Catalog:
    path = find_catalog_file(
        DATA, MANUAL_GEARBOX.file_substring, MANUAL_GEARBOX.path_contains
    )
    return Catalog(MANUAL_GEARBOX, path, DATA)


class TestGearboxMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = _gearbox()

    def test_row_count_is_merged_total(self):
        self.assertEqual(len(self.cat.rows), 59)

    def test_shakti_rows_were_added(self):
        # MG + vendor letter, same convention as MOR's MR + vendor letter:
        # Q = Q-tork (30), T = Transtork (11) — the 41 pre-existing rows —
        # and S = Shakti (18), the 2026-07-29 drop.
        codes = [str(r.get("c1")) for r in self.cat.rows]
        for prefix, expected in (("MGQ", 30), ("MGT", 11), ("MGS", 18)):
            found = sum(1 for c in codes if c.startswith(prefix))
            self.assertEqual(found, expected, f"{prefix}: {found} != {expected}")

    def test_codes_are_unique(self):
        codes = [str(r.get("c1")) for r in self.cat.rows]
        self.assertEqual(len(codes), len(set(codes)))

    def test_three_makes_are_selectable(self):
        makes = {str(r.get("c2")) for r in self.cat.rows}
        self.assertIn("Torque Transmissioin (Shakti)", makes)
        self.assertIn("Transtork", makes)
        self.assertIn("Q-tork", makes)

    def test_cascade_resolves_without_ambiguity(self):
        seen = {}
        for r in self.cat.rows:
            key = (str(r.get("c2")), str(r.get("c7")), str(r.get("c3")))
            seen.setdefault(key, []).append(str(r.get("c1")))
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        self.assertEqual(dupes, {}, f"ambiguous make/torque/model: {dupes}")


if __name__ == "__main__":
    unittest.main()
