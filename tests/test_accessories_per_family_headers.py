"""Consolidated-sheet families must use their OWN embedded header row.

`Dashboard accessories.xlsx` stacks ~14 families into one sheet, each preceded
by its own header row (a row whose Code column literally reads "Code"). The
loader used to discard all 12 of those as garbage and then label EVERY family
with row 1 — which is ALR's schema. The result was systematically wrong labels
on every consolidated family, with a different effective offset per family:

    LSB            "Make" = SB202L2            -> "Model of LSB"
    LSB            "Port Size" = Cherry/...    -> "Make & Model of Switches"
    LSB            "Tempreture" = IP 67        -> "Enclosure"
    Volume Booster "Make" = SS316              -> "Material of Construction"
    Volume Booster "Port Size" = 10 bar        -> "Max. Presssure"
    Silencer       "Make" = Brass              -> "Material of Construction"
    CFLG           "Port Size" = Carbon Steel  -> "Flange Material"

Fixed 2026-08-02 by capturing each family's header row and applying it to that
family's rows. Values are untouched — this is purely a labelling fix.

Source typos ("Max. Presssure", "Tempreture", "Diaphram Material") are kept
verbatim: the app mirrors the datasheet and does not silently correct it.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from accessories import load_accessories  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"

# (family, code-or-None-for-first-row, label, expected value)
EXPECTED_LABELLING = [
    ("LSB", "Model of LSB", "SB202L2"),
    ("LSB", "Movement", "Rotary"),
    ("LSB", "Make & Model of Switches", "Cherry / Honeywell (Micro Switch)"),
    ("LSB", "Housing Material", "Aluminium Die Cast"),
    ("LSB", "Enclosure", "IP 67"),
    ("Volume Booster", "Material of Construction", "SS316"),
    ("Volume Booster", "Port Size", '1/4" BSP'),
    ("Volume Booster", "Max. Presssure", "10 bar"),
    ("Silencer", "Material of Construction", "Brass"),
    ("Silencer", "Port Connection", "BSP"),
    ("CFLG", "Flange Type", "Flat Face"),
    ("CFLG", "Flange Material", "Carbon Steel (CS)"),
    ("BKT", "Bracket Material", "Carbon Steel (CS)"),
    ("BKT", "Adaptor Material", "En24+Plating"),
]

# Labels that only ever belonged to ALR's schema and must no longer leak onto
# families that have no such attribute.
ALR_ONLY_LEAKS = {
    "LSB": ["Signal Pressure", "Diaphram Material", "Tempreture", "Leakage"],
    "Volume Booster": ["Make", "Model"],
    "Silencer": ["Make", "Model"],
    "CFLG": ["Port Size", "Signal Pressure", "Max. Presssure", "Type"],
    "BKT": ["Model", "Material of Construction", "Port Size", "Signal Pressure"],
}


class TestPerFamilyHeaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_accessories(DATA)
        cls.first = {}
        for r in cls.data["rows"]:
            cls.first.setdefault(r["family"], r)

    def _attrs(self, family):
        return {a["label"]: a["value"] for a in self.first[family]["attrs"]}

    def test_labels_come_from_each_familys_own_header(self):
        for family, label, value in EXPECTED_LABELLING:
            attrs = self._attrs(family)
            self.assertIn(label, attrs, f"{family}: missing {label!r}")
            self.assertEqual(attrs[label], value, f"{family}.{label}")

    def test_alr_schema_no_longer_leaks_onto_other_families(self):
        for family, leaked in ALR_ONLY_LEAKS.items():
            attrs = self._attrs(family)
            for label in leaked:
                self.assertNotIn(
                    label, attrs,
                    f"{family} still labelled with ALR's {label!r}",
                )

    def test_row_counts_unchanged_by_the_relabelling(self):
        counts = {f["key"]: f["count"] for f in self.data["families"]}
        for family, expected in (
            ("LSB", 36), ("BKT", 8), ("CFLG", 8), ("Volume Booster", 8),
            ("Silencer", 6), ("FRG", 2), ("ALR", 2), ("QEV", 2), ("FCV", 1),
        ):
            self.assertEqual(counts[family], expected, family)
        self.assertEqual(len(self.data["rows"]), 405)

    def test_alr_itself_is_still_correct(self):
        """ALR supplied row 1, so it was the one family already labelled right —
        it must not regress."""
        attrs = self._attrs("ALR")
        self.assertIn("Material of Construction", attrs)
        self.assertIn("Port Size", attrs)


if __name__ == "__main__":
    unittest.main()
