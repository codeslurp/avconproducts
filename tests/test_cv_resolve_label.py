"""Per-series actuator card labels in Catalog.resolve() (pure logic — no Excel)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import Catalog, CONTROL_VALVE  # noqa: E402


def _row(**cols):
    base = {f"c{c}": "" for c in range(1, 60)}
    base.update(cols)
    return base


def _cat(rows):
    cat = Catalog.__new__(Catalog)          # bypass __init__/Excel load
    cat.config = CONTROL_VALVE
    cat.rows = rows
    cat._key_to_col = {k: idx for k, idx, _ in CONTROL_VALVE.cascade}
    return cat


# Minimal picks that uniquely select a hand-built row (6 fields).
def _picks(series):
    return {"series": series, "body_material": "WCB", "trim_material": "SS",
            "characteristics": "On-Off", "end_connection": "Flanged",
            "face_to_face": "ISA"}


def _cols(series, a, b):
    return {"c2": "SKU", "c3": "CAT", "c5": series, "c7": "WCB", "c8": "SS",
            "c10": "On-Off", "c11": "Flanged", "c14": "ISA", "c46": a, "c47": b}


class TestResolveLabels(unittest.TestCase):
    def test_5016_distinct_models_two_cards_with_port_labels(self):
        cat = _cat([_row(**_cols("5016A205", "MSD-630 D", "MSD-430 A"))])
        d = cat.resolve(_picks("5016A205"))
        self.assertEqual([p["label"] for p in d["paired_actuators"]],
                         ["A Port Close", "B Port Close"])

    def test_5016_identical_models_one_card_aport_label(self):
        cat = _cat([_row(**_cols("5016A205", "MSD-630 D", "MSD-630 D"))])
        d = cat.resolve(_picks("5016A205"))
        self.assertEqual([p["label"] for p in d["paired_actuators"]],
                         ["A Port Close"])

    def test_5012_keeps_generic_labels(self):
        # Distinct MSD families (MSD-200 vs MSD-430) so both cards survive dedup.
        cat = _cat([_row(**_cols("5012A205", "MSD-200 C", "MSD-430 A"))])
        d = cat.resolve(_picks("5012A205"))
        self.assertEqual([p["label"] for p in d["paired_actuators"]],
                         ["Fail-Safe Close (Normally Closed)",
                          "Fail-Safe Open (Normally Open)"])


if __name__ == "__main__":
    unittest.main()
