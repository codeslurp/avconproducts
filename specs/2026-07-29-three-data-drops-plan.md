# Three Data Drops (2026-07-29) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate three data files dropped on 2026-07-29 — merge a third
vendor range into Manual Override (23 -> 36 SKUs) and into Gear Box (41 -> 59
rows), and add a new `Trunnion Mounted` ball-valve type (168 SKUs) — without
changing any existing catalog.

**Architecture:** Two of the three drops are additive vendor ranges folded into
existing families using mechanisms the codebase already has (a new `merge_all`
flag on the accessory loader; an `ExtraRowSource` on the gear box config). The
third is a new `ValveTypeConfig` sibling to Metal and Plastic. A new optional
`pending_note` config field carries the "data not yet supplied" message so the
result panel shows no empty widgets.

**Tech Stack:** Python 3.14, `openpyxl`, Flask + Jinja2, vanilla JS, `unittest`
run under `pytest`. No new dependencies.

**Spec:** `specs/2026-07-29-three-data-drops-design.md`

## Global Constraints

- **Python interpreter:** bare `py`/`python`/`python3` do NOT work in this bash
  shell. Every command below uses
  `PY="/c/Users/skarnik/AppData/Local/Python/pythoncore-3.14-64/python.exe"`.
- **Repo:** `/c/Users/skarnik/repos/avconproducts` is the single source of
  truth. Branch `feat/2026-07-29-data-drops`, based on `main` @ `94eb04b`.
- **Baseline test state:** `20 passed, 2 failed` on clean `main`. The 2 failures
  are pre-existing and unrelated to this work; Task 1 repairs them so the rest of
  the plan can use "all green" as its gate.
- **Baseline row counts** (must not change except where stated):
  `ball` = 3892, `manual_gearbox` = 41 -> 59, MOR family = 23 -> 36.
- **Never patch source workbooks.** Data defects are reported in
  `docs/engineering-followups/`, never corrected in code. Verbatim load always.
- **Never invent a value.** If a source cell is wrong or missing, omit it and
  note it; do not guess what it should have been.
- **Exact display strings**, copied verbatim:
  - type label: `Trunnion Mounted`
  - pending note: `Torque, actuator sizing, and design standard pending — R03 data.`

---

### Task 1: Repair the pre-existing red test baseline

Two tests assert the 5016 control-valve cascade override has **6** fields. Commits
`da05d58` ("expand cascade from 6 to 11 fields") and `94eb04b` ("add valve_kv and
certification to cascade (13 fields total)") changed the config to **13** without
updating them. Nothing to do with this feature — but a red suite makes "no new
failures" unverifiable, so fix it first.

The current value, read from the config, is exactly:

```python
['series', 'size', 'body_material', 'trim_material', 'seat_material',
 'characteristics', 'flow_direction', 'end_connection', 'face_to_face',
 'port_size', 'valve_kv', 'bonnet_type', 'certification']
```

**Files:**
- Modify: `tests/test_cv_config.py`
- Modify: `tests/test_cv_serialize.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a green baseline (`22 passed`) that every later task gates on.

- [ ] **Step 1: Run the suite and record the exact failures**

```bash
cd /c/Users/skarnik/repos/avconproducts
PY="/c/Users/skarnik/AppData/Local/Python/pythoncore-3.14-64/python.exe"
"$PY" -m pytest tests/ -q 2>&1 | tail -8
```

Expected: `2 failed, 20 passed`, naming
`test_cv_config.py::TestControlValveOverrides::test_5016_override_lists_six_fields`
and `test_cv_serialize.py::TestSerialize::test_serialized_catalog_has_overrides`.

- [ ] **Step 2: Update the expected list in `tests/test_cv_config.py`**

Replace the whole `test_5016_override_lists_six_fields` method with:

```python
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
```

- [ ] **Step 3: Update `tests/test_cv_serialize.py` to match**

Replace lines 27-34 — the whole `test_serialized_catalog_has_overrides` method —
with:

```python
    def test_serialized_catalog_has_overrides(self):
        d = build_static._serialize_catalog("control_valve", self.cv)
        self.assertEqual(d["cascade_override_key"], "series")
        self.assertEqual(
            d["cascade_overrides"]["5016A"],
            ["series", "size", "body_material", "trim_material",
             "seat_material", "characteristics", "flow_direction",
             "end_connection", "face_to_face", "port_size", "valve_kv",
             "bonnet_type", "certification"],
        )
```

Do not touch `test_paired_has_series_labels` or
`test_section_summary_has_overrides` — both already pass.

- [ ] **Step 4: Run the suite and verify it is green**

```bash
"$PY" -m pytest tests/ -q 2>&1 | tail -4
```

Expected: `22 passed`, 0 failed.

- [ ] **Step 5: Commit**

```bash
git add tests/test_cv_config.py tests/test_cv_serialize.py
git commit -m "test: update stale 5016 cascade assertions from 6 to 13 fields

Pre-existing failures on main: da05d58 and 94eb04b expanded the 5016
override list to 13 fields without updating these two tests. No product
code changes."
```

---

### Task 2: Stage the three source files into the repo data tree

The files currently exist only in the OneDrive drop folder. The repo `data/`
tree is what the loaders read.

**Files:**
- Create: `data/Accessories/Manual Override Data for New Structure_R1_Updated.xlsx`
- Create: `data/Accessories/Gear Box Data for New Structure_R1.xlsx`
- Create: `data/Valve/Pune/Ball Valve Data Set/Ball Valve Data Sheet Structure 2094F TMBV_R03.xlsx`

**Interfaces:**
- Consumes: nothing.
- Produces: the three workbooks at the paths every later task's `file_substring`
  resolves against.

- [ ] **Step 1: Copy the three files**

```bash
cd /c/Users/skarnik/repos/avconproducts
DROP="/c/Users/skarnik/OneDrive - Tesla/Desktop/personalProjects/Product Code Finder/data"
cp "$DROP/Accessories/Manual Override Data for New Structure_R1_Updated.xlsx" data/Accessories/
cp "$DROP/Accessories/Gear Box Data for New Structure_R1.xlsx" data/Accessories/
cp "$DROP/Valve/Pune/Ball Valve Data Set/Ball Valve Data Sheet Structure 2094F TMBV_R03.xlsx" \
   "data/Valve/Pune/Ball Valve Data Set/"
```

- [ ] **Step 2: Verify the copies parse and hold the expected row counts**

```bash
PY="/c/Users/skarnik/AppData/Local/Python/pythoncore-3.14-64/python.exe"
"$PY" -c "
import openpyxl, warnings
from pathlib import Path
warnings.simplefilter('ignore')
checks = [
  ('data/Accessories/Manual Override Data for New Structure_R1_Updated.xlsx','MOR',13),
  ('data/Accessories/Gear Box Data for New Structure_R1.xlsx','MHG',18),
  ('data/Valve/Pune/Ball Valve Data Set/Ball Valve Data Sheet Structure 2094F TMBV_R03.xlsx','2094F TMBV NEW CODEING',168),
]
for f, sheet, want in checks:
    wb = openpyxl.load_workbook(Path(f), data_only=True, read_only=True)
    rows = [r for r in list(wb[sheet].iter_rows(values_only=True))[1:] if r and r[0] not in (None,'')]
    wb.close()
    status = 'OK' if len(rows)==want else 'MISMATCH'
    print(f'{status:9} {sheet:26} {len(rows):4d} rows (want {want})')
"
```

Expected: three `OK` lines. Any `MISMATCH` means the copy is wrong or the drop
file changed — stop and re-check before continuing.

- [ ] **Step 3: Commit**

```bash
git add data/
git commit -m "data: add 2026-07-29 drops (MOR Shakti, Gear Box Shakti, 2094F TMBV R03)

- Manual Override _R1_Updated: 13 Shakti MRS* rows (third vendor)
- Gear Box _R1: 18 Shakti MGS* rows
- 2094F TMBV_R03: 168 trunnion-mounted ball valve SKUs

Data only; no loader wiring yet."
```

---

### Task 3: Manual Override merges to 36 SKUs

`_load_extra_family` returns only the newest file matching `file_substring`
(`app/accessories.py:228-235`). Both MOR files match, so the new drop would
silently replace the 23 existing SKUs with 13.

**Files:**
- Modify: `app/accessories.py:61-83` (add `merge_all` to the Manual Override entry)
- Modify: `app/accessories.py:226-282` (split `_load_extra_family`, add merge path)
- Test: `tests/test_accessories_mor_merge.py`

**Interfaces:**
- Consumes: the staged files from Task 2.
- Produces: `_read_family_file(path: Path, src: dict) -> list[dict[str, Any]]` —
  reads ONE workbook into `[{code, family, attrs}]`.
  `_load_extra_family(acc_dir: Path, src: dict) -> list[dict[str, Any]]` keeps
  its existing signature and return type.

- [ ] **Step 1: Write the failing test**

Create `tests/test_accessories_mor_merge.py`:

```python
"""MOR loads all three vendor ranges, not just the newest file.

Regression guard: _load_extra_family used to return only the most-recently-
modified file matching "Manual Override". The 2026-07-29 Shakti drop
(_R1_Updated, 13 MRS* rows) would therefore have silently replaced the 23
Q-Tork/Transtork rows in _R1 — with a log line that read like success.
The three ranges are disjoint and all three are live products.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from accessories import load_accessories  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


class TestMorMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [
            r for r in load_accessories(DATA)["rows"] if r["family"] == "MOR"
        ]

    def test_all_three_vendor_ranges_load(self):
        self.assertEqual(len(self.rows), 36)

    def test_each_vendor_prefix_present_in_full(self):
        codes = [r["code"] for r in self.rows]
        for prefix, expected in (("MRQ", 13), ("MRT", 10), ("MRS", 13)):
            found = sum(1 for c in codes if c.startswith(prefix))
            self.assertEqual(found, expected, f"{prefix}: {found} != {expected}")

    def test_codes_are_unique(self):
        codes = [r["code"] for r in self.rows]
        self.assertEqual(len(codes), len(set(codes)))

    def test_family_count_reflects_merge(self):
        fams = {f["key"]: f for f in load_accessories(DATA)["families"]}
        self.assertEqual(fams["MOR"]["count"], 36)
```

- [ ] **Step 2: Run it and verify it fails**

```bash
PY="/c/Users/skarnik/AppData/Local/Python/pythoncore-3.14-64/python.exe"
"$PY" -m pytest tests/test_accessories_mor_merge.py -q 2>&1 | tail -6
```

Expected: FAIL — `36 != 13` (the newest-wins loader returned only the Shakti file).

- [ ] **Step 3: Extract the single-file reader**

In `app/accessories.py`, rename the existing `_load_extra_family` to
`_read_family_file` and change its signature to take a resolved path. Replace
the function's first 8 lines — from `def _load_extra_family(...)` through
`path = sorted(cands, ...)[0]` — with:

```python
def _read_family_file(path: Path, src: dict) -> list[dict[str, Any]]:
    """Read ONE single-family accessory workbook into [{code, family, attrs}]."""
```

Leave the entire rest of the function body unchanged, starting at
`with warnings.catch_warnings():`.

- [ ] **Step 4: Add the new dispatcher**

Immediately above `_read_family_file`, add:

```python
def _load_extra_family(acc_dir: Path, src: dict) -> list[dict[str, Any]]:
    """Load one accessory family from its dedicated file(s).

    Default: the most-recently-modified match wins — a later export supersedes
    an earlier one for the same family.

    With `merge_all: True`: EVERY match is read, oldest first, and rows are
    merged on `code`. Used where separate files hold DISJOINT vendor ranges of
    one family rather than successive revisions of the same range — MOR ships
    as Q-Tork + Transtork (R1, 23 rows) plus Shakti (R1_Updated, 13 rows) with
    zero code overlap. Newest-wins on a genuine duplicate code preserves
    supersede semantics, and every override is logged rather than silent.
    """
    cands = [
        p for p in acc_dir.rglob("*.xls*")
        if src["file_substring"] in p.name and not p.name.startswith("~$")
        and (not src.get("exclude") or src["exclude"] not in p.name)
    ]
    if not cands:
        return []
    if not src.get("merge_all"):
        newest = sorted(cands, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        return _read_family_file(newest, src)

    merged: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for path in sorted(cands, key=lambda p: p.stat().st_mtime):
        for row in _read_family_file(path, src):
            if row["code"] in merged:
                print(
                    f"[valve-selector] Accessories: {src['family']} code "
                    f"{row['code']} overridden by newer {path.name}.",
                    flush=True,
                )
            merged[row["code"]] = row
    print(
        f"[valve-selector] Accessories: merged {len(merged)} {src['family']} "
        f"rows from {len(cands)} file(s).",
        flush=True,
    )
    return list(merged.values())
```

`OrderedDict` is already imported at `app/accessories.py:27`.

- [ ] **Step 5: Turn the flag on for Manual Override only**

In `EXTRA_ACCESSORY_SOURCES`, replace the Manual Override line with:

```python
    # merge_all: the two MOR files hold DISJOINT vendor ranges, not successive
    # revisions — R1 = 13 Q-Tork (MRQ*) + 10 Transtork (MRT*), R1_Updated = 13
    # Shakti (MRS*), zero overlap. Newest-wins would silently drop 23 SKUs.
    {"file_substring": "Manual Override", "sheet": "MOR", "family": "MOR", "code_col": 1, "merge_all": True},
```

- [ ] **Step 6: Run the test and verify it passes**

```bash
"$PY" -m pytest tests/test_accessories_mor_merge.py -q 2>&1 | tail -4
```

Expected: `4 passed`.

- [ ] **Step 7: Run the whole suite for regressions**

```bash
"$PY" -m pytest tests/ -q 2>&1 | tail -4
```

Expected: `26 passed`, 0 failed. Any other family changing row count is a bug —
`merge_all` is opt-in and set on one entry only.

- [ ] **Step 8: Commit**

```bash
git add app/accessories.py tests/test_accessories_mor_merge.py
git commit -m "feat(accessories): merge all Manual Override vendor files (23 -> 36)

_load_extra_family took only the newest file matching the substring, so the
2026-07-29 Shakti drop would have silently replaced 23 Q-Tork/Transtork SKUs
with 13 Shakti ones. Split out _read_family_file and add an opt-in merge_all
flag, set on the MOR source only. Duplicate codes are newest-wins AND logged."
```

---

### Task 4: Gear Box merges to 59 rows

**Files:**
- Modify: `app/catalog.py:1304-1326` (`MANUAL_GEARBOX`)
- Test: `tests/test_gearbox_merge.py`

**Interfaces:**
- Consumes: the staged Gear Box file from Task 2; `ExtraRowSource`
  (`app/catalog.py:103-121`); `_apply_extra_rows` (`app/catalog.py:1533`).
- Produces: nothing new for later tasks.

- [ ] **Step 1: Write the failing test**

Create `tests/test_gearbox_merge.py`:

```python
"""Gear Box (MHG) folds in the Shakti range dropped 2026-07-29.

The two sources are schema-identical (same 14 headers) and disjoint:
  Actuator/Manual Actuator/MHG Manual Gear Box ...  41 rows, MGT*, WGX-*
  Accessories/Gear Box Data for New Structure_R1   18 rows, MGS*, SE-*
The bare substring "Gear Box Data for New Structure" matches BOTH filenames, so
the ExtraRowSource must be pinned with path_contains="Accessories" — otherwise
it re-reads the master, adds nothing, and reports success.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import Catalog, find_catalog_file, MANUAL_GEARBOX  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"


def _gearbox() -> Catalog:
    path = find_catalog_file(
        DATA, MANUAL_GEARBOX.file_substring, MANUAL_GEARBOX.path_contains
    )
    return Catalog(MANUAL_GEARBOX, path, DATA)


class TestGearboxMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = _gearbox()

    def test_row_count_is_merged_total(self):
        self.assertEqual(len(self.cat.rows), 59)

    def test_shakti_rows_were_added(self):
        codes = [str(r.get("c1")) for r in self.cat.rows]
        self.assertEqual(sum(1 for c in codes if c.startswith("MGS")), 18)
        self.assertEqual(sum(1 for c in codes if c.startswith("MGT")), 41)

    def test_codes_are_unique(self):
        codes = [str(r.get("c1")) for r in self.cat.rows]
        self.assertEqual(len(codes), len(set(codes)))

    def test_three_makes_are_selectable(self):
        makes = {str(r.get("c2")) for r in self.cat.rows}
        self.assertIn("Torque Transmissioin (Shakti)", makes)
        self.assertIn("Transtork", makes)
        self.assertIn("Q-tork", makes)

    def test_cascade_resolves_without_ambiguity(self):
        seen = {}
        for r in self.cat.rows:
            key = (str(r.get("c2")), str(r.get("c7")), str(r.get("c3")))
            seen.setdefault(key, []).append(str(r.get("c1")))
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        self.assertEqual(dupes, {}, f"ambiguous make/torque/model: {dupes}")
```

Note `Q-tork` is lower-case `t` in the MHG source (the MOR source spells the
same vendor `Q-Tork`). Both are loaded verbatim; see the engineering follow-up.

- [ ] **Step 2: Run it and verify it fails**

```bash
PY="/c/Users/skarnik/AppData/Local/Python/pythoncore-3.14-64/python.exe"
"$PY" -m pytest tests/test_gearbox_merge.py -q 2>&1 | tail -6
```

Expected: FAIL — `41 != 59`.

- [ ] **Step 3: Add the extra-row source**

In `app/catalog.py`, inside the `MANUAL_GEARBOX` config, add this immediately
after the `detail_columns=[...]` block (before the closing `)`):

```python
    # Shakti gear boxes (18 rows, MGS*/SE-*) dropped 2026-07-29 into
    # data/Accessories/. Schema-identical to the master (same 14 headers), so
    # columns map 1:1. path_contains is REQUIRED: the bare file_substring also
    # matches this catalog's OWN file ("MHG Manual Gear Box Data for New
    # Structure_R1.xlsx"), and picking that would add zero rows silently.
    extra_row_sources=(
        ExtraRowSource(
            file_substring="Gear Box Data for New Structure",
            sheet_marker="MHG",
            path_contains="Accessories",
            key_col=1, master_key_col=1,
            column_map=((1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8),(9,9)),
        ),
    ),
```

- [ ] **Step 4: Run the test and verify it passes**

```bash
"$PY" -m pytest tests/test_gearbox_merge.py -q 2>&1 | tail -4
```

Expected: `5 passed`.

- [ ] **Step 5: Run the whole suite**

```bash
"$PY" -m pytest tests/ -q 2>&1 | tail -4
```

Expected: `31 passed`, 0 failed.

- [ ] **Step 6: Commit**

```bash
git add app/catalog.py tests/test_gearbox_merge.py
git commit -m "feat(gearbox): fold Shakti MGS range into Gear Box MHG (41 -> 59)

ExtraRowSource pinned with path_contains='Accessories' — the bare substring
also matches the catalog's own master file, which would have added zero rows
without reporting a problem. Cascade verified 0 ambiguous across 59 rows."
```

---

### Task 5: `pending_note` config field

A per-type, static line of text rendered where the FOS card would sit. Needed by
Task 6; built and tested on its own so the plumbing is verified before a type
depends on it.

**Files:**
- Modify: `app/catalog.py:173-174` (add field to `ValveTypeConfig`)
- Modify: `app/server.py:58-74` (`_section_summary`)
- Modify: `tools/build_static.py:116-123` (`_section_summary`)
- Modify: `app/templates/index.html:226` (render after the `.codes` div)
- Test: `tests/test_pending_note.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ValveTypeConfig.pending_note: str | None = None`, surfaced to the
  template as `section.pending_note`. Task 6 sets it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pending_note.py`:

```python
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
```

- [ ] **Step 2: Run it and verify it fails**

```bash
PY="/c/Users/skarnik/AppData/Local/Python/pythoncore-3.14-64/python.exe"
"$PY" -m pytest tests/test_pending_note.py -q 2>&1 | tail -6
```

Expected: FAIL — `'pending_note' not found in {...}`.

- [ ] **Step 3: Add the field to `ValveTypeConfig`**

In `app/catalog.py`, immediately after the `bto_col: int = 39` line, add:

```python
    # Optional one-line notice rendered in the result panel, for types that ship
    # with data the source hasn't supplied yet. Used INSTEAD of blank cards: the
    # relevant columns are left out of detail_columns and this explains why.
    # Remove it (and restore the columns) when the source revision lands.
    pending_note: str | None = None
```

- [ ] **Step 4: Expose it in the Flask section summary**

In `app/server.py`, in `_section_summary`, add after the
`"show_bto_fos": cfg.show_bto_fos,` line:

```python
        "pending_note": cfg.pending_note,
```

- [ ] **Step 5: Expose it in the static-build section summary**

In `tools/build_static.py`, in `_section_summary` (the one at line 116, NOT
`_serialize_catalog`), add after its `"show_bto_fos": cfg.show_bto_fos,` line:

```python
        "pending_note": cfg.pending_note,
```

- [ ] **Step 6: Render it in the template**

In `app/templates/index.html`, immediately after the `</div>` that closes the
`.codes` block (line 226) and before `<div class="alt-note" hidden></div>`, add:

```html
            {% if section.pending_note %}
            <p class="pending-note">{{ section.pending_note }}</p>
            {% endif %}
```

- [ ] **Step 7: Style it**

Append to `app/static/styles.css`:

```css
/* One-line notice for catalogs shipped with known-absent source data
   (see ValveTypeConfig.pending_note). Sits where the FOS card would be. */
.pending-note {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
  font-style: italic;
  opacity: 0.75;
}
```

- [ ] **Step 8: Run the test and verify it passes**

```bash
"$PY" -m pytest tests/test_pending_note.py -q 2>&1 | tail -4
```

Expected: `4 passed`.

- [ ] **Step 9: Run the whole suite**

```bash
"$PY" -m pytest tests/ -q 2>&1 | tail -4
```

Expected: `35 passed`, 0 failed.

- [ ] **Step 10: Commit**

```bash
git add app/catalog.py app/server.py tools/build_static.py \
        app/templates/index.html app/static/styles.css tests/test_pending_note.py
git commit -m "feat: add optional ValveTypeConfig.pending_note

A per-type line rendered where the FOS card sits, for catalogs that ship with
data the source has not supplied. Plumbed through both _section_summary
builders (Flask and static build) — they enumerate fields separately, so a new
field needs adding in both. Defaults to None; no existing type sets it."
```

---

### Task 6: New type — Pune > Ball Valve > Trunnion Mounted

**Files:**
- Modify: `app/catalog.py` (add `BALL_VALVE_TRUNNION` after `BALL_VALVE_PLASTIC`)
- Modify: `app/catalog.py:1349-1368` (`VALVE_TYPES`)
- Modify: `app/templates/index.html:57` (icon chain)
- Test: `tests/test_ball_trunnion.py`

**Interfaces:**
- Consumes: the staged 2094F file (Task 2); `pending_note` (Task 5).
- Produces: catalog key `ball_trunnion`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ball_trunnion.py`:

```python
"""2094F TMBV — Trunnion Mounted ball valves, 168 SKUs, added 2026-07-29.

R03 supplies columns 1-36 and 38 only. Torque (39-42), Run, Top PCD, the stem
block (44-48), Product Group (37) and every actuator column are empty in all
168 rows, so this type shows no FOS card and no recommended actuators.
Column 12 (Design Standard) is excluded too — it is corrupted by an Excel
autofill drag (trailing "& N" runs 2..169). See the engineering follow-up.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import (  # noqa: E402
    Catalog, find_catalog_file, BALL_VALVE, BALL_VALVE_TRUNNION, VALVE_TYPES,
)

DATA = Path(__file__).resolve().parent.parent / "data"


def _load(cfg) -> Catalog:
    path = find_catalog_file(DATA, cfg.file_substring, cfg.path_contains)
    return Catalog(cfg, path, DATA)


class TestTrunnionCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = _load(BALL_VALVE_TRUNNION)

    def test_loads_all_skus(self):
        self.assertEqual(len(self.cat.rows), 168)

    def test_bare_codes_are_unique(self):
        codes = [str(r.get("c1")) for r in self.cat.rows]
        self.assertEqual(len(set(codes)), 168)

    def test_reads_the_trunnion_file_not_the_metal_master(self):
        self.assertIn("2094F TMBV", self.cat.file_path.name)

    def test_cascade_resolves_every_sku_uniquely(self):
        cols = [c for _k, c, _l in BALL_VALVE_TRUNNION.cascade]
        seen = {}
        for r in self.cat.rows:
            key = tuple(str(r.get(f"c{c}")) for c in cols)
            seen.setdefault(key, []).append(str(r.get("c1")))
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        self.assertEqual(dupes, {}, f"ambiguous cascade combos: {dupes}")

    def test_no_fos_card_and_no_paired_actuators(self):
        self.assertFalse(BALL_VALVE_TRUNNION.show_bto_fos)
        self.assertEqual(BALL_VALVE_TRUNNION.paired_actuators, ())

    def test_pending_note_is_set(self):
        self.assertEqual(
            BALL_VALVE_TRUNNION.pending_note,
            "Torque, actuator sizing, and design standard pending — R03 data.",
        )

    def test_empty_and_corrupt_columns_are_not_shown(self):
        shown = {c for c, _label in BALL_VALVE_TRUNNION.detail_columns}
        for col in (12, 37, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48):
            self.assertNotIn(col, shown, f"column {col} must not be displayed")

    def test_every_shown_column_actually_has_data(self):
        shown = [c for c, _label in BALL_VALVE_TRUNNION.detail_columns]
        for col in shown:
            filled = sum(
                1 for r in self.cat.rows
                if r.get(f"c{col}") not in (None, "")
            )
            self.assertGreater(filled, 0, f"column {col} is empty in all rows")

    def test_registered_in_the_picker_under_ball_valve(self):
        self.assertIn(BALL_VALVE_TRUNNION, VALVE_TYPES)
        self.assertEqual(BALL_VALVE_TRUNNION.group, "Pune")
        self.assertEqual(BALL_VALVE_TRUNNION.subgroup, "Ball Valve")
        self.assertEqual(BALL_VALVE_TRUNNION.label, "Trunnion Mounted")

    def test_has_its_own_picker_icon(self):
        src = os.path.join(
            os.path.dirname(__file__), "..", "app", "templates", "index.html"
        )
        with open(src, encoding="utf-8") as fh:
            self.assertIn('item.key == "ball_trunnion"', fh.read())


class TestMetalUnaffected(unittest.TestCase):
    def test_metal_row_count_unchanged(self):
        self.assertEqual(len(_load(BALL_VALVE).rows), 3892)

    def test_metal_still_reads_the_master_workbook(self):
        self.assertIn("NEW OG", _load(BALL_VALVE).file_path.name)
```

- [ ] **Step 2: Run it and verify it fails**

```bash
PY="/c/Users/skarnik/AppData/Local/Python/pythoncore-3.14-64/python.exe"
"$PY" -m pytest tests/test_ball_trunnion.py -q 2>&1 | tail -6
```

Expected: FAIL at import — `cannot import name 'BALL_VALVE_TRUNNION'`.

- [ ] **Step 3: Add the config**

In `app/catalog.py`, immediately after the `BALL_VALVE_PLASTIC` config's closing
`)`, add:

```python
# 2094F TMBV — Trunnion Mounted, soft seated. Third sibling under the "Ball
# Valve" subgroup, so the menu reads Pune > Ball Valve > Metal / Plastic /
# Trunnion Mounted. Ships from its OWN workbook: the series is absent from the
# metal master (.xlsm holds 2030F/2060F/2070F/2090F only), and its columns
# 49-58 carry Additional-Specification/cost headers where the master has the
# nine actuator columns. file_substring is unambiguous — the master is matched
# by "NEW OG" and the plastic file by "Ball Valve Plastic".
#
# R03 populates columns 1-36 and 38 ONLY. Product Group (37), the torque block
# (39-42), Run (43), Top PCD (44) and the stem block (45-48) are empty in all
# 168 rows, hence show_bto_fos=False and no paired_actuators. Column 12
# (Design Standard) is withheld as corrupt — see
# docs/engineering-followups/2026-07-29-2094f-trunnion-data-gaps.md.
BALL_VALVE_TRUNNION = ValveTypeConfig(
    key="ball_trunnion",
    label="Trunnion Mounted",
    category="Valves",
    group="Pune",
    subgroup="Ball Valve",
    file_substring="Ball Valve Data Sheet Structure 2094F TMBV",
    path_contains="Pune",
    sheet_marker="2094F TMBV NEW CODEING",
    show_bto_fos=False,
    pending_note="Torque, actuator sizing, and design standard pending — R03 data.",
    # Same eight fields as the metal master. Verified 0 ambiguous across all 168
    # rows: the data factorizes as 4 series x 3 body x 7 seat x 2 end connection,
    # with size determined by series. Ball Material, Characteristics and Ball
    # Type are single-valued in R03 and auto-fill (see app.js Picker.setFieldValue);
    # they are kept for parity and to stay correct when R04 adds variety.
    cascade=[
        ("series",          4,  "Series"),
        ("size",            5,  "Valve Size"),
        ("body_material",   6,  "Body Material"),
        ("ball_material",   7,  "Ball Material"),
        ("seat_material",   8,  "Seat Material"),
        ("characteristics", 9,  "Characteristics"),
        ("end_connection", 10,  "End Connections"),
        ("ball_type",      22,  "Ball Type"),
    ],
    detail_columns=[
        (1, "Bare Valve Code"), (2, "Catalogue Code"), (3, "Make"),
        (11, "Valve Type"), (13, "Face to Face"),
        (14, "Port Size"), (15, "No. of Ports"), (16, "Valve Kv (m³/hr)"),
        (17, "Body Style"), (18, "Flow Direction"), (19, "End Piece Material"),
        (20, "Type of Bonnet"), (21, "Stem Material"),
        (23, "Gland Packing"), (24, "Body Packing"),
        (25, "Flange Dimensions"), (26, "Flange Drilling"),
        (27, "Pressure Rating"), (28, "Operating Temp Range (°C)"),
        (29, "Hardware"), (30, "Valve Paint"),
        (31, "Testing Standard"), (32, "Leakage Class"),
        (33, "Body Test Pressure (barg)"), (34, "Body Test Media"),
        (35, "Seat Leakage Test Pressure (barg)"), (36, "Seat Leakage Test Media"),
        (38, "Certification"),
    ],
)
```

- [ ] **Step 4: Register it in `VALVE_TYPES`**

In the `VALVE_TYPES` list, add `BALL_VALVE_TRUNNION,` on the line directly after
`BALL_VALVE_PLASTIC,` so the picker order reads Metal, Plastic, Trunnion Mounted.

- [ ] **Step 5: Add the picker icon**

In `app/templates/index.html`, in the `item.key` icon chain, add this branch
directly after the `butterfly_double_offset` branch:

```html
            {% elif item.key == "ball_trunnion" %}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5" fill="currentColor"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/></svg>
```

A circle-and-ball like Metal, plus top and bottom trunnion stubs.

- [ ] **Step 6: Run the test and verify it passes**

```bash
"$PY" -m pytest tests/test_ball_trunnion.py -q 2>&1 | tail -4
```

Expected: `12 passed`.

- [ ] **Step 7: Run the whole suite**

```bash
"$PY" -m pytest tests/ -q 2>&1 | tail -4
```

Expected: `47 passed`, 0 failed.

- [ ] **Step 8: Commit**

```bash
git add app/catalog.py app/templates/index.html tests/test_ball_trunnion.py
git commit -m "feat(valves): add Trunnion Mounted ball valve type (2094F TMBV, 168 SKUs)

New sibling under Pune > Ball Valve alongside Metal and Plastic. The series is
absent from the metal master, so it ships from its own workbook. Metal's
8-field cascade reused and verified 0 ambiguous across all 168 rows.

R03 has no torque or actuator data: show_bto_fos=False, no paired actuators,
and a pending_note replaces the omitted cards. Design Standard (col 12) is
withheld as corrupt. Metal row count asserted unchanged at 3892."
```

---

### Task 7: Engineering follow-up for the source-data defects

**Files:**
- Create: `docs/engineering-followups/2026-07-29-2094f-trunnion-data-gaps.md`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing consumed by code.

- [ ] **Step 1: Write the follow-up**

Create the file with exactly this content:

```markdown
# Engineering follow-up: 2094F TMBV R03 + Shakti vendor data

**Date:** 2026-07-29
**Sources:**
- `data/Valve/Pune/Ball Valve Data Set/Ball Valve Data Sheet Structure 2094F TMBV_R03.xlsx`
- `data/Accessories/Gear Box Data for New Structure_R1.xlsx`
- `data/Accessories/Manual Override Data for New Structure_R1_Updated.xlsx`

These are defects in the source datasheets, not app bugs. The app loads what the
datasheets contain; where a value is wrong it is withheld rather than guessed.

## 1. `Design Standard` corrupted by an Excel autofill drag (blocking)

Column 12 of the `2094F TMBV NEW CODEING` sheet reads, on all 168 rows:

    ASME B16.34, API 6D, BS EN ISO 17292, ASME VIII Div. 1, EN12516- 1 & N

where `N` runs **2, 3, 4 ... 169** — strictly increasing, one per row. The string
is otherwise byte-identical across every row. The `2090F` sheet in the metal
master has exactly **1** distinct value in the same column
(`ASME B16.34, API 6D, BS EN ISO 17292`).

**Effect in the app:** the column is **omitted** from the Trunnion Mounted result
panel. It is not normalised in code, because the intended base string cannot be
determined from the available sources — `& 2` and the master's shorter form are
both plausible, and choosing one would be a guess.

**Requested fix:** re-issue column 12 with the correct constant value in R04.

## 2. Unpopulated columns in 2094F R03

Empty in all 168 rows:

| Col | Header |
| --- | --- |
| 37 | Product Group |
| 39-42 | BTO / ETO / BTC / ETC |
| 43 | Run |
| 44 | Top PCD |
| 45-48 | Stem Shape / Dimension / Orientation / Potrution (mm) |

Columns 49-58 are also empty, and carry `Additional Specification 1 @3.5` ...
`Offer Rate (INR)` headers where the master series sheets carry the nine
actuator columns (`Double Acting Actuator 1-3`, `Single Acting Fail Safe
Close/Open 1-3`). The stray `@3.5` in the column 49 header suggests the actuator
block was overwritten rather than deliberately omitted.

**Effect in the app:** no torque/FOS card and no recommended-actuator chips for
this series. The panel shows: *"Torque, actuator sizing, and design standard
pending — R03 data."*

**Requested fix:** supply torque, Top PCD, the stem block, and the actuator
columns in R04, in the master's column positions.

## 3. Vendor name misspelled

Both Shakti files spell the make `Torque Transmissioin (Shakti)` —
**Transmissioin** should be **Transmission**. This string is a user-visible
option in the Gear Box `Make` dropdown.

Loaded verbatim: correcting it in code would desync the app from the datasheet
and be re-broken by the next export.

**Requested fix:** correct the spelling at source in both files.

## 4. Inconsistent vendor spelling across files (minor)

The same vendor is spelled `Q-tork` in
`MHG Manual Gear Box Data for New Structure_R1.xlsx` and `Q-Tork` in
`Manual Override Data for New Structure_R1.xlsx`. Both appear verbatim in their
respective dropdowns. Not corrected in code.

**Requested fix:** pick one spelling and apply it in both datasheets.
```

- [ ] **Step 2: Commit**

```bash
git add docs/engineering-followups/2026-07-29-2094f-trunnion-data-gaps.md
git commit -m "docs: engineering follow-up for 2094F R03 and Shakti data defects

Design Standard autofill corruption (trailing '& N' runs 2..169 across the 168
rows), 11 unpopulated columns, and two vendor-name spelling issues. Reported,
not patched — the app withholds the corrupt column rather than guessing it."
```

---

### Task 8: Static build, verification, and deploy

**Files:**
- Modify: `docs/` (regenerated by the build script)

**Interfaces:**
- Consumes: everything from Tasks 1-7.
- Produces: the deployed site.

- [ ] **Step 1: Run the app locally and check all three changes**

```bash
cd /c/Users/skarnik/repos/avconproducts
PY="/c/Users/skarnik/AppData/Local/Python/pythoncore-3.14-64/python.exe"
"$PY" app/server.py
```

In the browser, confirm:
1. Valves picker shows **Pune > Ball Valve > Metal / Plastic / Trunnion Mounted**,
   Trunnion with its own icon.
2. Selecting Trunnion Mounted resolves to a single SKU and shows **no** FOS card,
   **no** actuator chips, and the pending note.
3. Actuators > Manual > Gear Box (MHG) offers **three** makes.
4. The accessories MOR family lists **36** items.

Stop the server with Ctrl-C.

- [ ] **Step 2: Build the static bundle**

```bash
"$PY" tools/build_static.py 2>&1 | tail -30
```

Expected: a `wrote ball_trunnion.json — 168 rows` line, `manual_gearbox` at 59
rows, `ball` unchanged at 3,892, and `accessories.json` up by 13 rows.

- [ ] **Step 3: Verify the generated output before pushing**

```bash
"$PY" -c "
import json
from pathlib import Path
d = Path('docs/data')
t = json.loads((d/'ball_trunnion.json').read_text(encoding='utf-8'))
print('trunnion rows       :', len(t['rows']))
print('show_bto_fos        :', t['show_bto_fos'])
print('paired_actuators    :', len(t['paired_actuators']))
print('cascade fields      :', [c['key'] for c in t['cascade']])
print('col 12 in details   :', any(c['col']==12 for c in t['detail_columns']))
print('gearbox rows        :', len(json.loads((d/'manual_gearbox.json').read_text(encoding='utf-8'))['rows']))
print('ball rows           :', len(json.loads((d/'ball.json').read_text(encoding='utf-8'))['rows']))
acc = json.loads((d/'accessories.json').read_text(encoding='utf-8'))
print('MOR rows            :', sum(1 for r in acc['rows'] if r['family']=='MOR'))
"
grep -c 'ball_trunnion' docs/index.html
grep -c 'pending-note' docs/index.html
```

Expected: `168`, `False`, `0`, the eight cascade keys, `False`, `59`, `3892`,
`36`; and both `grep -c` counts at least `1`.

- [ ] **Step 4: Run the full suite one last time**

```bash
"$PY" -m pytest tests/ -q 2>&1 | tail -4
```

Expected: `47 passed`, 0 failed.

- [ ] **Step 5: Commit the build output**

```bash
git add docs/
git commit -m "build: regenerate static bundle for the 2026-07-29 data drops

ball_trunnion.json (168 rows) added; manual_gearbox 41 -> 59; accessories MOR
23 -> 36; ball unchanged at 3892."
```

- [ ] **Step 6: Push and merge**

```bash
git push -u origin feat/2026-07-29-data-drops
```

Then merge to `main` (fast-forward or PR, per preference) and push `main`.

- [ ] **Step 7: Wait for GitHub Pages, then verify LIVE bytes**

Wait ~95 seconds after the push to `main`, then:

```bash
BASE="https://codeslurp.github.io/avconproducts"
curl -s "$BASE/data/ball_trunnion.json?cb=$(date +%s)" | head -c 200; echo
curl -s "$BASE/index.html?cb=$(date +%s)" | grep -c 'ball_trunnion'
```

Expected: real JSON (not a 404 page), and a non-zero grep count. If either
fails, wait another 60 s and retry before investigating — do not conclude the
deploy is broken from a single early check.

- [ ] **Step 8: Hard-refresh in a browser and re-run the Step 1 checks**

Open the live site, hard-refresh (Ctrl-Shift-R), and repeat the four visual
checks from Step 1 against the deployed build.

---

## Success Criteria

| Metric | Before | After |
| --- | --- | --- |
| Tests | 20 passed, 2 failed | 47 passed, 0 failed |
| MOR accessory family | 23 | 36 |
| `manual_gearbox` | 41 | 59 |
| `ball_trunnion` | absent | 168 |
| `ball` (metal) | 3892 | **3892 — unchanged** |
| Source workbooks modified | — | **none** |
