"""Control Valve gains 5043A/5044A/5045A/5046A (R1 drop, 2026-07-30).

Four new Globe Type / Metal Seated series, 1,040 SKUs, consolidated into
Dashboard_V2 by tools/consolidate_control_valve.py. They ship with the spec
region as empty "Additional Specification" slots, so they carry no Fail-Safe
MSD models — the one attribute the existing series DO have and these don't.
(Thrust/Torque/Mounting PCD/Stem Diameter are empty catalog-wide, including on
5012A, so they are not a gap specific to this drop.)

Also pins a PRE-EXISTING defect in 5066A so a future drop that fixes it (or
worsens it) is noticed — see the engineering follow-up.
"""
import collections
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import (  # noqa: E402
    Catalog, find_catalog_file, CONTROL_VALVE,
)

DATA = Path(__file__).resolve().parent.parent / "data"

NEW_SERIES = {"5043A": 440, "5044A": 320, "5045A": 80, "5046A": 200}
PRE_EXISTING_TOTAL = 17681


def _catalog() -> Catalog:
    path = find_catalog_file(
        DATA, CONTROL_VALVE.file_substring, CONTROL_VALVE.path_contains
    )
    return Catalog(CONTROL_VALVE, path, DATA)


class TestNewSeries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = _catalog()
        cls.by_family = collections.defaultdict(list)
        for r in cls.cat.rows:
            cls.by_family[str(r.get("c5"))[:5]].append(r)

    def test_total_row_count(self):
        self.assertEqual(
            len(self.cat.rows), PRE_EXISTING_TOTAL + sum(NEW_SERIES.values())
        )

    def test_each_new_series_row_count(self):
        for fam, expected in NEW_SERIES.items():
            self.assertEqual(len(self.by_family[fam]), expected, fam)

    def test_all_bare_codes_unique_catalog_wide(self):
        codes = [str(r.get("c2")) for r in self.cat.rows]
        self.assertEqual(len(codes), len(set(codes)))

    def test_new_series_cascade_is_unambiguous(self):
        cols = {k: c for k, c, _ in CONTROL_VALVE.cascade}
        keys = [k for k, _c, _l in CONTROL_VALVE.cascade]
        for fam in NEW_SERIES:
            counts = collections.Counter(
                tuple(str(r.get(f"c{cols[k]}")) for k in keys)
                for r in self.by_family[fam]
            )
            ambiguous = sum(v - 1 for v in counts.values() if v > 1)
            self.assertEqual(ambiguous, 0, f"{fam}: {ambiguous} ambiguous")

    def test_new_series_have_no_override_and_use_base_cascade(self):
        for fam in NEW_SERIES:
            self.assertNotIn(fam, CONTROL_VALVE.cascade_overrides)

    def test_new_series_carry_no_failsafe_actuator_models(self):
        # Cols 46/47 back the two paired-actuator cards; empty here, so app.js
        # hides that section rather than rendering blank chips.
        for fam in NEW_SERIES:
            for col in (46, 47):
                filled = sum(
                    1 for r in self.by_family[fam]
                    if r.get(f"c{col}") not in (None, "")
                )
                self.assertEqual(filled, 0, f"{fam} c{col}")

    def test_new_series_populate_stroke(self):
        # Stroke (c43) IS supplied, on every row, same as the existing series.
        for fam in NEW_SERIES:
            filled = sum(
                1 for r in self.by_family[fam] if r.get("c43") not in (None, "")
            )
            self.assertEqual(filled, len(self.by_family[fam]), fam)

    def test_thrust_torque_pcd_are_catalog_wide_empty_not_a_new_gap(self):
        """Thrust (c40), Torque (c41), Mounting PCD (c42) and Stem Diameter
        (c44) are empty for EVERY control valve series, including 5012A — they
        are not something this drop specifically lacks. Pinned so that if a
        future drop starts supplying them, we notice and surface them."""
        for col in (40, 41, 42, 44):
            filled = sum(
                1 for r in self.cat.rows if r.get(f"c{col}") not in (None, "")
            )
            self.assertEqual(filled, 0, f"c{col} now has data — surface it")


class TestPreExistingSeriesUnchanged(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = _catalog()
        cls.by_family = collections.defaultdict(list)
        for r in cls.cat.rows:
            cls.by_family[str(r.get("c5"))[:5]].append(r)

    def test_existing_series_row_counts(self):
        expected = {
            "5012A": 10801, "5012B": 2160, "5016A": 1280,
            "5016B": 640, "5061A": 2160, "5066A": 640,
        }
        for fam, n in expected.items():
            self.assertEqual(len(self.by_family[fam]), n, fam)

    def test_5066a_duplicate_codes_are_unchanged(self):
        """PRE-EXISTING defect, present before the 5043-5046 drop and live today.

        5066A ships 640 rows that are only 320 distinct products: every product
        appears under two bare codes (offset +5, e.g. 5066AD0001 / 5066AD0006)
        and is identical in EVERY other column. Half the series is therefore
        unreachable in the picker. Verified identical before and after this
        drop by diffing the committed docs/data/control_valve.json.

        Pinned at exactly 320 so a future drop that fixes or worsens it fails
        loudly. See docs/engineering-followups/
        2026-07-30-control-valve-5043-5046-data-gaps.md
        """
        rows = self.by_family["5066A"]
        groups = collections.defaultdict(list)
        for r in rows:
            groups[tuple(
                str(r.get(f"c{i}")) for i in range(1, 60) if i != 2
            )].append(str(r.get("c2")))
        dupes = [v for v in groups.values() if len(v) > 1]
        self.assertEqual(len(dupes), 320)
        self.assertTrue(all(len(v) == 2 for v in dupes))


if __name__ == "__main__":
    unittest.main()
