"""Verify the consolidated V2 restores 5016 B-Port actuator data and keeps
5016 A-Port, without disturbing 5012/other series."""
import os
import unittest
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
V2 = os.path.join(
    ROOT, "data", "Valve", "Pune", "Control Valve Data Set",
    "Control Valve Dashboard_V2.xlsx",
)


def _blank(s):
    return int((s.isna() | (s.astype(str).str.strip().str.lower().isin(["", "nan"]))).sum())


class TestCv5016BPortRestore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_excel(V2, sheet_name="Control Valve", header=0, dtype=object)
        cls.codes = cls.df["Bare Valve Code"].astype(str)

    def _series(self, prefix):
        return self.df[self.codes.str.startswith(prefix)]

    def test_5016_bport_populated(self):
        sub = self._series("5016")
        self.assertEqual(len(sub), 1920)
        self.assertEqual(_blank(sub["Fail Safe Close / A-Port Close"]), 0)
        self.assertEqual(_blank(sub["Fail Safe Open / B-Port Close"]), 0)

    def test_5016_aport_bport_differ_on_some_rows(self):
        sub = self._series("5016")
        a = sub["Fail Safe Close / A-Port Close"].astype(str).str.strip()
        b = sub["Fail Safe Open / B-Port Close"].astype(str).str.strip()
        self.assertGreater(int((a != b).sum()), 0)

    def test_total_rows(self):
        # 17,681 through the 5016/5012 R*_Updated era; +1,040 on 2026-07-30 when
        # 5043A/5044A/5045A/5046A were added (440+320+80+200); -320 the same day
        # when the de-duplicated 5066A re-drop replaced 640 rows with 320. See
        # tests/test_control_valve_5043_5046.py for the per-series breakdown.
        self.assertEqual(len(self.df), 18401)

    def test_new_series_did_not_disturb_5016(self):
        self.assertEqual(len(self._series("5016")), 1920)


if __name__ == "__main__":
    unittest.main()
