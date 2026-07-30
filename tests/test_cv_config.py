"""Unit tests for the per-series config helpers (pure logic)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import CONTROL_VALVE, PairedActuator  # noqa: E402


class TestControlValveOverrides(unittest.TestCase):
    def test_5016_override_lists_thirteen_fields(self):
        ov = CONTROL_VALVE.cascade_overrides
        self.assertIn("5016A", ov)
        self.assertIn("5016B", ov)
        expected = [
            "series", "size", "body_material", "trim_material", "seat_material",
            "characteristics", "flow_direction", "end_connection", "face_to_face",
            "port_size", "valve_kv", "bonnet_type", "certification",
        ]
        self.assertEqual(ov["5016A"], expected)
        self.assertEqual(ov["5016B"], expected)

    def test_override_key_is_series(self):
        self.assertEqual(CONTROL_VALVE.cascade_override_key, "series")

    def test_override_keys_are_subset_of_base_cascade(self):
        base = {k for k, _c, _l in CONTROL_VALVE.cascade}
        for keys in CONTROL_VALVE.cascade_overrides.values():
            self.assertTrue(set(keys) <= base)

    def test_paired_label_for_prefix(self):
        pa = PairedActuator(
            model_col=46, target_field="model", target_type="pneumatic_msd",
            require_prefix="MSD-", label="Fail-Safe Close (Normally Closed)",
            series_labels={"5016A": "A Port Close", "5016B": "A Port Close"},
        )
        self.assertEqual(pa.label_for("5016A205"), "A Port Close")
        self.assertEqual(pa.label_for("5012A205"), "Fail-Safe Close (Normally Closed)")
        self.assertEqual(pa.label_for(None), "Fail-Safe Close (Normally Closed)")


if __name__ == "__main__":
    unittest.main()
