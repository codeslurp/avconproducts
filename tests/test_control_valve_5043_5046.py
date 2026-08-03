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

# 17,681 before the 5043-5046 drop; +1,040 for it. 5066A dipped to 320 on the
# interim 2026-07-30 fix, then returned to 640 with R3 (2026-08-02), which
# supplied the missing Face-to-Face attribute instead of deleting rows.
EXPECTED_TOTAL = 18721


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
        self.assertEqual(len(self.cat.rows), EXPECTED_TOTAL)

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

    def test_5066a_duplication_is_fixed(self):
        """5066A shipped 640 rows that were only 320 distinct products — each
        product under two bare codes identical in all 58 other columns, so half
        the code space was unreachable.

        Reported to Pune and fixed twice. The interim file (2026-07-30) deleted
        320 rows, which also dropped 320 real products and remapped 160 codes.
        R3 (2026-08-02) is the correct fix: it keeps all 640 codes and supplies
        the attribute that was actually missing — Face to Face differs on 320
        rows (e.g. 5066AD0001 "DIN EN 558 SERIES-1 #150" vs 5066AD0006
        "ISA 75.08.01 #150"). They were never duplicates.

        Asserts the fix holds: 640 rows, none identical once the code is ignored.
        """
        rows = self.by_family["5066A"]
        groups = collections.defaultdict(list)
        for r in rows:
            groups[tuple(
                str(r.get(f"c{i}")) for i in range(1, 60) if i != 2
            )].append(str(r.get("c2")))
        dupes = {k: v for k, v in groups.items() if len(v) > 1}
        self.assertEqual(len(rows), 640)
        self.assertEqual(dupes, {}, f"5066A duplication is back: {list(dupes.values())[:3]}")

    def test_5066a_spec_columns_restored_from_r2(self):
        """R3 ships the spec region blank, so the four values are restored from
        _R2 by `enrich`, joined on bare valve code (see UPDATED_DROPS in
        tools/consolidate_control_valve.py). Safe because R3 and _R2 share an
        identical 640-code set and identical product identity per code apart
        from Face to Face — each code gets back what AVCON published for it.

        Guards against a future drop silently losing them again.
        """
        rows = self.by_family["5066A"]
        for col, label in (
            (45, "Max Shut-off Pressure"),
            (46, "Fail Safe Close / A-Port Close"),
            (47, "Fail Safe Open / B-Port Close"),
            (48, "Control Pressure"),
        ):
            filled = sum(1 for r in rows if r.get(f"c{col}") not in (None, ""))
            self.assertEqual(filled, 640, f"{label} (c{col}) only {filled}/640")

    def test_whole_catalog_is_unambiguous(self):
        """The project invariant: every SKU must be reachable. Each series uses
        its cascade_overrides field list if it has one, else the base cascade.

        This was VIOLATED by 320 rows until 2026-07-30 (the 5066A duplication
        above). It now holds catalog-wide — keep it that way.
        """
        cols = {k: c for k, c, _ in CONTROL_VALVE.cascade}
        by_series = collections.defaultdict(list)
        for r in self.cat.rows:
            by_series[str(r.get("c5"))].append(r)
        offenders = {}
        for series, rows in by_series.items():
            keys = (CONTROL_VALVE.cascade_overrides.get(series[:5])
                    or [k for k, _c, _l in CONTROL_VALVE.cascade])
            counts = collections.Counter(
                tuple(str(r.get(f"c{cols[k]}")) for k in keys) for r in rows
            )
            ambiguous = sum(v - 1 for v in counts.values() if v > 1)
            if ambiguous:
                offenders[series] = ambiguous
        self.assertEqual(offenders, {}, f"ambiguous series: {offenders}")


if __name__ == "__main__":
    unittest.main()
