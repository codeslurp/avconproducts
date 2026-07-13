"""Nullable cascade field: Certification offers a "None" option so blank-cert
SKUs (e.g. 5012AE0581) are reachable and don't get force-matched to IBR."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import Catalog, CONTROL_VALVE, CASCADE_NULL_OPTION  # noqa: E402


def _row(**cols):
    base = {f"c{c}": "" for c in range(1, 60)}
    base.update(cols)
    return base


def _cat(rows):
    cat = Catalog.__new__(Catalog)
    cat.config = CONTROL_VALVE
    cat.rows = rows
    cat._key_to_col = {k: idx for k, idx, _ in CONTROL_VALVE.cascade}
    return cat


# Identical 11 non-cert fields; one row blank cert, one IBR.
def _pair():
    common = {"c5": "5012A255", "c7": "WCB", "c8": "SS410", "c9": "CA40",
              "c10": "Equal Percent", "c11": "Flanged", "c14": "ISA",
              "c15": "25", "c17": "10", "c19": "Flow to Open", "c21": "Standard"}
    blank = _row(c2="5012AE0581", c3="CAT-EQP", c39=None, **common)
    ibr = _row(c2="5012AE0E71", c3="CAT-EQP", c39="IBR", **common)
    return blank, ibr


_PICKS11 = {"series": "5012A255", "body_material": "WCB", "trim_material": "SS410",
            "seat_material": "CA40", "characteristics": "Equal Percent",
            "end_connection": "Flanged", "face_to_face": "ISA", "port_size": "25",
            "valve_kv": "10", "flow_direction": "Flow to Open", "bonnet_type": "Standard"}


class TestCertNoneOption(unittest.TestCase):
    def test_options_offer_none_and_ibr(self):
        cat = _cat(list(_pair()))
        opts = cat.options(_PICKS11)["certification"]
        self.assertIn("IBR", opts)
        self.assertIn(CASCADE_NULL_OPTION, opts)

    def test_resolve_none_reaches_blank_sku(self):
        cat = _cat(list(_pair()))
        d = cat.resolve({**_PICKS11, "certification": CASCADE_NULL_OPTION})
        self.assertEqual(d["primary"], "5012AE0581")

    def test_resolve_ibr_reaches_ibr_sku(self):
        cat = _cat(list(_pair()))
        d = cat.resolve({**_PICKS11, "certification": "IBR"})
        self.assertEqual(d["primary"], "5012AE0E71")


if __name__ == "__main__":
    unittest.main()
