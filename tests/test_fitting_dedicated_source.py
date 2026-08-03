"""Tube & Fittings loads from its dedicated file, not the consolidated sheet.

The consolidated `Dashboard accessories.xlsx` stacks ~14 families under ONE
header row, so every family inherits whichever label that row happens to carry
in each column. For FITTING that mislabels the material: the sheet reports
`Model = SS304` where the datum is a material of construction.

The dedicated `Tube  Fitting Data for New Structure_R1.xlsx` (note the double
space in the filename) carries a per-family header row and labels it correctly.
Cell-diffed 2026-08-02: identical 6 codes, identical values, only the label
differs — so this migration is a pure labelling fix with no data change.

Same pattern already applied to Gland, MOR, Plug and THW FOR MSD.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from accessories import EXTRA_ACCESSORY_SOURCES, load_accessories  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"

EXPECTED = {
    "TS4GFS4G": ("Generic Make", "SS304"),
    "TS6GFS6G": ("Generic Make", "SS316"),
    "TS4VFS4W": ("Sandvik Make & Swagelok Make", "SS304"),
    "TS6VFS6W": ("Sandvik Make & Swagelok Make", "SS316"),
    "TS4RFS4W": ("Ratnamani Make & Swagelok Make", "SS304"),
    "TS6RFS6W": ("Ratnamani Make & Swagelok Make", "SS316"),
}


class TestFittingDedicatedSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [
            r for r in load_accessories(DATA)["rows"] if r["family"] == "FITTING"
        ]
        cls.by_code = {r["code"]: r for r in cls.rows}

    def test_registered_as_a_dedicated_source(self):
        fams = {s["family"] for s in EXTRA_ACCESSORY_SOURCES}
        self.assertIn("FITTING", fams)

    def test_all_six_codes_load_exactly_once(self):
        self.assertEqual(len(self.rows), 6)
        self.assertEqual(set(self.by_code), set(EXPECTED))

    def test_material_is_labelled_correctly_not_as_model(self):
        """The whole point of the migration: the consolidated sheet called this
        'Model'. Guard against a regression that puts FITTING back on it."""
        for code, (_make, material) in EXPECTED.items():
            attrs = {a["label"]: a["value"] for a in self.by_code[code]["attrs"]}
            self.assertIn("Material of Construction", attrs, code)
            self.assertNotIn("Model", attrs, f"{code} is back on the consolidated sheet")
            self.assertEqual(attrs["Material of Construction"], material, code)

    def test_make_survived_the_migration(self):
        for code, (make, _material) in EXPECTED.items():
            attrs = {a["label"]: a["value"] for a in self.by_code[code]["attrs"]}
            self.assertEqual(attrs["Make"], make, code)

    def test_family_count_still_six(self):
        fams = {f["key"]: f for f in load_accessories(DATA)["families"]}
        self.assertEqual(fams["FITTING"]["count"], 6)
        self.assertFalse(fams["FITTING"]["pending"])


if __name__ == "__main__":
    unittest.main()
