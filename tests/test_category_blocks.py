"""Unit tests for catalog.build_category_blocks (pure grouping logic)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import build_category_blocks  # noqa: E402


def _sec(key, category, subgroup, group=None):
    return {"key": key, "category": category, "subgroup": subgroup,
            "group": group, "row_count": 1}


class TestBuildCategoryBlocks(unittest.TestCase):
    def test_groups_by_category_then_subgroup(self):
        sections = [_sec("ball", "Valves", "Pune"), _sec("butterfly", "Valves", "Pune")]
        blocks = build_category_blocks(sections, {})
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["name"], "Valves")
        self.assertEqual(blocks[0]["subgroups"][0]["name"], "Pune")
        self.assertEqual(
            [m["key"] for m in blocks[0]["subgroups"][0]["members"]],
            ["ball", "butterfly"],
        )

    def test_planned_empty_subgroup_is_appended_with_placeholder(self):
        sections = [_sec("ball", "Valves", "Pune")]
        planned = {"Valves": [("Mumbai", "Data pending")]}
        subs = build_category_blocks(sections, planned)[0]["subgroups"]
        self.assertEqual(subs[-1]["name"], "Mumbai")
        self.assertEqual(subs[-1]["members"], [])
        self.assertEqual(subs[-1]["placeholder"], "Data pending")

    def test_planned_subgroup_suppressed_when_real_members_exist(self):
        sections = [_sec("ball", "Valves", "Pune"), _sec("m_ball", "Valves", "Mumbai")]
        planned = {"Valves": [("Mumbai", "Data pending")]}
        subs = build_category_blocks(sections, planned)[0]["subgroups"]
        mumbai = [s for s in subs if s["name"] == "Mumbai"]
        self.assertEqual(len(mumbai), 1)
        self.assertEqual([m["key"] for m in mumbai[0]["members"]], ["m_ball"])
        self.assertEqual(mumbai[0]["placeholder"], "")

    def test_pune_orders_before_planned_mumbai(self):
        sections = [_sec("ball", "Valves", "Pune")]
        planned = {"Valves": [("Mumbai", "Data pending")]}
        subs = build_category_blocks(sections, planned)[0]["subgroups"]
        self.assertEqual([s["name"] for s in subs], ["Pune", "Mumbai"])

    def test_blank_subgroups_under_different_groups_do_not_merge(self):
        # Pune-group families with no subgroup must NOT merge with a Mumbai-group
        # family that also has no subgroup (keyed by (group, subgroup)).
        sections = [
            _sec("ball", "Valves", None, group="Pune"),
            _sec("bf", "Valves", "Butterfly Valve", group="Pune"),
            _sec("bf_do", "Valves", "Butterfly Valve", group="Pune"),
            _sec("control", "Valves", None, group="Pune"),
            _sec("pharma", "Valves", "Mumbai"),
        ]
        subs = build_category_blocks(sections, {})[0]["subgroups"]
        # blocks: ("Pune","") [ball,control], ("Pune","Butterfly Valve") [bf,bf_do],
        #         ("","Mumbai") [pharma]
        blank_pune = [s for s in subs if s["name"] == "" and s["group"] == "Pune"]
        self.assertEqual(len(blank_pune), 1)
        self.assertEqual([m["key"] for m in blank_pune[0]["members"]], ["ball", "control"])
        bfly = [s for s in subs if s["name"] == "Butterfly Valve"]
        self.assertEqual(len(bfly), 1)
        self.assertEqual(bfly[0]["group"], "Pune")
        self.assertEqual([m["key"] for m in bfly[0]["members"]], ["bf", "bf_do"])
        mumbai = [s for s in subs if s["name"] == "Mumbai"]
        self.assertEqual([m["key"] for m in mumbai[0]["members"]], ["pharma"])

    def test_planned_category_absent_from_sections_is_skipped(self):
        sections = [_sec("rp", "Actuators", "Pneumatic")]
        planned = {"Valves": [("Mumbai", "Data pending")]}
        names = [b["name"] for b in build_category_blocks(sections, planned)]
        self.assertEqual(names, ["Actuators"])  # no phantom Valves category


if __name__ == "__main__":
    unittest.main()
