"""Verify cascade_overrides + paired series_labels are serialized for the
static bundle and the template section summary (pure logic — no Excel load)."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from catalog import CONTROL_VALVE  # noqa: E402
import build_static  # noqa: E402


class _StubCatalog:
    """Minimal stand-in for Catalog: only what the serializers read."""
    def __init__(self, config):
        self.config = config
        self.rows = []
        self.file_path = Path("Control Valve Dashboard_V2.xlsx")


class TestSerialize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cv = _StubCatalog(CONTROL_VALVE)

    def test_serialized_catalog_has_overrides(self):
        d = build_static._serialize_catalog("control_valve", self.cv)
        self.assertEqual(d["cascade_override_key"], "series")
        self.assertEqual(
            d["cascade_overrides"]["5016A"],
            ["series", "body_material", "trim_material",
             "characteristics", "end_connection", "face_to_face"],
        )

    def test_paired_has_series_labels(self):
        d = build_static._serialize_catalog("control_valve", self.cv)
        by_col = {p["model_col"]: p for p in d["paired_actuators"]}
        self.assertEqual(by_col[46]["series_labels"]["5016A"], "A Port Close")
        self.assertEqual(by_col[47]["series_labels"]["5016B"], "B Port Close")

    def test_section_summary_has_overrides(self):
        s = build_static._section_summary("control_valve", self.cv)
        self.assertEqual(s["cascade_overrides"]["5016B"][0], "series")
        self.assertEqual(s["cascade_override_key"], "series")


if __name__ == "__main__":
    unittest.main()
