"""pending_note is an optional per-type line shown when a catalog ships with
known-absent data (e.g. no torque figures yet). It must default to None, and
must reach the template through BOTH section-summary builders — the Flask one
and the static-build one, which enumerate their fields separately."""
import os
import sys
import unittest
from dataclasses import fields

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import BALL_VALVE, ValveTypeConfig  # noqa: E402


class TestPendingNoteField(unittest.TestCase):
    def test_field_exists_and_defaults_to_none(self):
        names = {f.name for f in fields(ValveTypeConfig)}
        self.assertIn("pending_note", names)
        self.assertIsNone(BALL_VALVE.pending_note)

    def test_flask_section_summary_exposes_it(self):
        # Read the source rather than importing server.py — importing it loads
        # every catalog from Excel at module scope, which is slow and would
        # make this pure-config test depend on the data files.
        src = os.path.join(
            os.path.dirname(__file__), "..", "app", "server.py"
        )
        with open(src, encoding="utf-8") as fh:
            self.assertIn('"pending_note": cfg.pending_note', fh.read())

    def test_static_build_section_summary_exposes_it(self):
        src = os.path.join(
            os.path.dirname(__file__), "..", "tools", "build_static.py"
        )
        with open(src, encoding="utf-8") as fh:
            self.assertIn('"pending_note": cfg.pending_note', fh.read())

    def test_template_renders_it(self):
        src = os.path.join(
            os.path.dirname(__file__), "..", "app", "templates", "index.html"
        )
        with open(src, encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn("section.pending_note", html)
        self.assertIn("pending-note", html)


if __name__ == "__main__":
    unittest.main()
