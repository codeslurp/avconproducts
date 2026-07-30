"""2094F TMBV — Trunnion Mounted ball valves, 168 SKUs, added 2026-07-29.

R03 supplies columns 1-36 and 38 only. Torque (39-42), Run, Top PCD, the stem
block (44-48), Product Group (37) and every actuator column are empty in all
168 rows, so this type shows no FOS card and no recommended actuators.
Column 12 (Design Standard) is excluded too — it is corrupted by an Excel
autofill drag (trailing "& N" runs 2..169). See the engineering follow-up.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import (  # noqa: E402
    Catalog, find_catalog_file, BALL_VALVE, BALL_VALVE_TRUNNION, VALVE_TYPES,
)

DATA = Path(__file__).resolve().parent.parent / "data"


def _load(cfg) -> Catalog:
    path = find_catalog_file(DATA, cfg.file_substring, cfg.path_contains)
    return Catalog(cfg, path, DATA)


class TestTrunnionCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = _load(BALL_VALVE_TRUNNION)

    def test_loads_all_skus(self):
        self.assertEqual(len(self.cat.rows), 168)

    def test_bare_codes_are_unique(self):
        codes = [str(r.get("c1")) for r in self.cat.rows]
        self.assertEqual(len(set(codes)), 168)

    def test_reads_the_trunnion_file_not_the_metal_master(self):
        self.assertIn("2094F TMBV", self.cat.file_path.name)

    def test_cascade_resolves_every_sku_uniquely(self):
        cols = [c for _k, c, _l in BALL_VALVE_TRUNNION.cascade]
        seen = {}
        for r in self.cat.rows:
            key = tuple(str(r.get(f"c{c}")) for c in cols)
            seen.setdefault(key, []).append(str(r.get("c1")))
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        self.assertEqual(dupes, {}, f"ambiguous cascade combos: {dupes}")

    def test_no_fos_card_and_no_paired_actuators(self):
        self.assertFalse(BALL_VALVE_TRUNNION.show_bto_fos)
        self.assertEqual(BALL_VALVE_TRUNNION.paired_actuators, ())

    def test_pending_note_is_set(self):
        self.assertEqual(
            BALL_VALVE_TRUNNION.pending_note,
            "Torque, actuator sizing, and design standard pending — R03 data.",
        )

    def test_empty_and_corrupt_columns_are_not_shown(self):
        shown = {c for c, _label in BALL_VALVE_TRUNNION.detail_columns}
        for col in (12, 37, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48):
            self.assertNotIn(col, shown, f"column {col} must not be displayed")

    def test_every_shown_column_actually_has_data(self):
        shown = [c for c, _label in BALL_VALVE_TRUNNION.detail_columns]
        for col in shown:
            filled = sum(
                1 for r in self.cat.rows
                if r.get(f"c{col}") not in (None, "")
            )
            self.assertGreater(filled, 0, f"column {col} is empty in all rows")

    def test_registered_in_the_picker_under_ball_valve(self):
        self.assertIn(BALL_VALVE_TRUNNION, VALVE_TYPES)
        self.assertEqual(BALL_VALVE_TRUNNION.group, "Pune")
        self.assertEqual(BALL_VALVE_TRUNNION.subgroup, "Ball Valve")
        self.assertEqual(BALL_VALVE_TRUNNION.label, "Trunnion Mounted")

    def test_has_its_own_picker_icon(self):
        src = os.path.join(
            os.path.dirname(__file__), "..", "app", "templates", "index.html"
        )
        with open(src, encoding="utf-8") as fh:
            self.assertIn('item.key == "ball_trunnion"', fh.read())


class TestMetalUnaffected(unittest.TestCase):
    def test_metal_row_count_unchanged(self):
        self.assertEqual(len(_load(BALL_VALVE).rows), 3892)

    def test_metal_still_reads_the_master_workbook(self):
        self.assertIn("NEW OG", _load(BALL_VALVE).file_path.name)


if __name__ == "__main__":
    unittest.main()
