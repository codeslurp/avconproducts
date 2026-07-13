# Control Valve 5016 — per-series cascade + dual actuator cards — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For Control Valve series 5016A/5016B only, collapse the picker to 6 selection fields and show two recommended-actuator cards ("A Port Close" / "B Port Close"), leaving all other series unchanged.

**Architecture:** A new `cascade_overrides` config (keyed on the Series value) drives per-series field visibility in `app/static/app.js` (fields are hidden/skipped, not removed from the DOM). A new `series_labels` field on `PairedActuator` gives per-series card labels, mirrored in `app/catalog.py` `resolve()` and `docs/static/catalog-engine.js`. The 5016 B-Port actuator column (blanked by AVCON in R4_Updated) is restored from the original R4 file via an `enrich` step in the consolidation tool.

**Tech Stack:** Python 3.14 (`py`), pandas, Flask (dev), static JSON + vanilla JS engine (deployed via GitHub Pages `docs/`). Tests: `unittest` under `tests/`.

## Global Constraints

- 0-ambiguous invariant: a full cascade selection resolves to exactly one Catalogue code. The 6-field 5016 set is already verified 0-ambiguous (5016A: 320 tuples, 5016B: 320 tuples, 0 ambiguous). Re-verify after build.
- Only `control_valve` may change behavior. 5012A/B, 5061A, 5066A keep the 12-field form and existing actuator labels ("Fail-Safe Close (Normally Closed)" / "Fail-Safe Open (Normally Open)").
- Cost/pricing columns (56–59) stay excluded from cascade, detail, and JSON.
- `app/catalog.py` `resolve()` and `docs/static/catalog-engine.js` `resolve()` must stay in sync (Appendix C #2).
- `app/static/app.js` is the single JS source; `build_static.py` copies it into `docs/static/app.js`. Never hand-edit `docs/static/app.js`. `docs/static/catalog-engine.js` is hand-maintained (not copied) — edit it directly.
- `docs/` is the deployed GitHub Pages bundle; never put plans/specs there.
- Deploy-verify flow: `py tools/consolidate_control_valve.py` → `py tools/build_static.py` → `py -m pytest tests/ -q` → commit/push → wait ~95s → verify live build stamp + JSON, hard-refresh browser.
- The controlling field for per-series overrides is `series` (col 5). Series value examples: `5016A205`, `5016B205` — the override keys must match how the Series **cascade value** is stored. VERIFY in Task 2 Step 1 what the Series dropdown value actually is (full `Series` col-5 string like `5016A205`, not `5016A`) and key the overrides on a prefix match accordingly.

---

### Task 1: Restore 5016 B-Port actuator data (consolidation enrich)

**Files:**
- Modify: `tools/consolidate_control_valve.py` (UPDATED_DROPS entry for the 5016 file; `_updated_drop_frames`)
- Test: `tests/test_cv_enrich.py` (create)

**Interfaces:**
- Consumes: original R4 file `Control Valve Data for New Structure 5016A-B_24.12.2025_R4.xlsx` (`working` tab, columns `Bare Valve Code`, `Fail Safe Open`), present at `data/Valve/Pune/Control Valve Data Set/`.
- Produces: `Control Valve Dashboard_V2.xlsx` where 5016 canonical col 47 (`Fail Safe Open / B-Port Close`) is populated from the original R4 `Fail Safe Open` column, joined by Bare Valve Code.

- [ ] **Step 1: Add an `enrich` spec to the 5016 UPDATED_DROPS entry**

In `tools/consolidate_control_valve.py`, extend the 5016 dict in `UPDATED_DROPS` (currently maps `Fail Safe Open / B-Port Close` → `None`). Add an `enrich` key and change the spec_map so the B-Port slot is filled by enrichment, not blank:

```python
    {
        "file": "Control Valve Data for New Structure 5016A-B_24.12.2025_R4_Updated.xlsx",
        "sheets": {"5016A CV ": "5016A", "5016B CV": "5016B"},
        "spec_map": {
            "Max Shut-off Pressure": None,
            "Fail Safe Close / A-Port Close": "A Port Close / B Port Close",
            "Fail Safe Open / B-Port Close": None,   # filled via `enrich` below
            "Control Pressure": None,
            "Control Pressure (Fail Safe Open)": None,
        },
        # Restore the B-Port (Open) MSD column AVCON blanked in R4_Updated, from
        # the original R4 working tab, joined by Bare Valve Code. Distinct from
        # A-Port on ~50% of SKUs. (User direction 2026-07-12: two actuator cards.)
        "enrich": [{
            "canonical": "Fail Safe Open / B-Port Close",
            "from_file": "Control Valve Data for New Structure 5016A-B_24.12.2025_R4.xlsx",
            "from_sheet": "working",
            "from_col": "Fail Safe Open",
            "key_col": "Bare Valve Code",
        }],
    },
```

Leave the 5012 entry unchanged (no `enrich` key).

- [ ] **Step 2: Implement enrichment in `_updated_drop_frames`**

In `_updated_drop_frames`, after `out` is built for each sheet and before `frames.append(out)`, apply any `enrich` specs for this drop. Add a module-level helper and call it:

```python
def _enrich_column(out: pd.DataFrame, spec: dict) -> tuple[pd.DataFrame, bool]:
    """Fill out[spec['canonical']] from another workbook, joined by Bare Valve
    Code. Returns (out, ok). ok is False (with a printed [FAIL]) if the source
    file/sheet/column is missing or any out-row key fails to join."""
    src_path = CV_DIR / spec["from_file"]
    if not src_path.is_file():
        print(f"[FAIL] enrich: source file not found: {src_path}")
        return out, False
    try:
        src = pd.read_excel(src_path, sheet_name=spec["from_sheet"], header=0, dtype=object)
    except Exception as e:
        print(f"[FAIL] enrich: cannot read {src_path.name}::{spec['from_sheet']}: {e}")
        return out, False
    src.columns = [_norm(c) for c in src.columns]
    for need in (spec["key_col"], spec["from_col"]):
        if need not in src.columns:
            print(f"[FAIL] enrich: column {need!r} absent in {spec['from_file']}")
            return out, False
    lut = {
        _norm(k): v
        for k, v in zip(src[spec["key_col"]], src[spec["from_col"]])
        if _norm(k) not in ("", "Bare Valve Code")
    }
    keys = out[spec["key_col"]].map(_norm)
    missing = [k for k in keys if k not in lut]
    if missing:
        print(f"[FAIL] enrich: {len(missing)} key(s) not found in source "
              f"(e.g. {missing[:3]}) for {spec['canonical']!r}")
        return out, False
    out[spec["canonical"]] = keys.map(lut).values
    return out, True
```

And in the per-sheet loop of `_updated_drop_frames`, right before `frames.append(out)`:

```python
        for espec in drop.get("enrich", []):
            out, eok = _enrich_column(out, espec)
            if not eok:
                return [], False
```

Also update the closing `note:` print so it no longer claims Control-Pressure/B-Port are always blank; make it accurate, e.g.:

```python
    print("        note: updated-format drops carry Fail-Safe Close/Open MSD "
          "columns (5016 B-Port restored from original R4); Max Shut-off / "
          "Control Pressure blank.")
```

- [ ] **Step 3: Write the failing test**

Create `tests/test_cv_enrich.py`:

```python
"""Verify the consolidated V2 restores 5016 B-Port actuator data and keeps
5016 A-Port, without disturbing 5012/other series."""
import os
import sys
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

    def test_total_rows_unchanged(self):
        self.assertEqual(len(self.df), 17681)
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `cd ~/repos/avconproducts && py -m pytest tests/test_cv_enrich.py -q`
Expected: FAIL on `test_5016_bport_populated` (`Fail Safe Open / B-Port Close` is currently 1920 blank) — because V2 hasn't been rebuilt yet.

- [ ] **Step 5: Re-run the consolidation to regenerate V2**

Run: `cd ~/repos/avconproducts && PYTHONUTF8=1 py tools/consolidate_control_valve.py`
Expected: report prints `[ok] 5016A` / `[ok] 5016B` from the R4_Updated tabs, no `[FAIL]`, `consolidated rows : 17681`, `[written] …Dashboard_V2.xlsx`.

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd ~/repos/avconproducts && py -m pytest tests/test_cv_enrich.py -q`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
cd ~/repos/avconproducts
git add tools/consolidate_control_valve.py tests/test_cv_enrich.py
git commit -m "data(control-valve): restore 5016 B-Port MSD from original R4 (enrich)"
```

---

### Task 2: Add per-series config fields (`cascade_overrides`, `series_labels`)

**Files:**
- Modify: `app/catalog.py` (`PairedActuator` dataclass ~44-54; `ValveTypeConfig` dataclass ~110-160; `CONTROL_VALVE` ~1152-1260)
- Test: `tests/test_cv_config.py` (create)

**Interfaces:**
- Produces:
  - `ValveTypeConfig.cascade_overrides: dict[str, list[str]] = field(default_factory=dict)` — maps a Series-value prefix → the ordered list of visible cascade keys.
  - `ValveTypeConfig.cascade_override_key: str | None = None` — the cascade key whose value selects the override (defaults to the first cascade key when `cascade_overrides` is non-empty).
  - `PairedActuator.series_labels: dict[str, str] = field(default_factory=dict)` — maps a Series-value prefix → the card label to use instead of `label`.
  - Helper `PairedActuator.label_for(series_value: str | None) -> str` returning the matching override (prefix match) or `self.label`.

- [ ] **Step 1: Confirm the Series cascade value format**

Run:
```bash
cd ~/repos/avconproducts && PYTHONUTF8=1 py - <<'PY'
import pandas as pd
p="data/Valve/Pune/Control Valve Data Set/Control Valve Dashboard_V2.xlsx"
df=pd.read_excel(p,sheet_name="Control Valve",header=0,dtype=object)
print(sorted(df.iloc[:,4].astype(str).str.strip().unique())[:12])  # col 5 = Series
PY
```
Expected: values like `['5012A205', '5012B205', '5016A205', '5016B205', '5061A155', '5066A205', ...]`. This confirms overrides must match by **prefix** (`5016A`, `5016B`), not exact equality — implement `label_for`/override lookup as "series_value startswith any override key".

- [ ] **Step 2: Write the failing test**

Create `tests/test_cv_config.py`:

```python
"""Unit tests for the per-series config helpers (pure logic)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import CONTROL_VALVE, PairedActuator  # noqa: E402


class TestControlValveOverrides(unittest.TestCase):
    def test_5016_override_lists_six_fields(self):
        ov = CONTROL_VALVE.cascade_overrides
        self.assertIn("5016A", ov)
        self.assertIn("5016B", ov)
        self.assertEqual(
            ov["5016A"],
            ["series", "body_material", "trim_material",
             "characteristics", "end_connection", "face_to_face"],
        )

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
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd ~/repos/avconproducts && py -m pytest tests/test_cv_config.py -q`
Expected: FAIL (`AttributeError: ... 'cascade_overrides'` / `label_for`).

- [ ] **Step 4: Add the dataclass fields + helper**

Ensure `from dataclasses import dataclass, field` is imported at the top of `app/catalog.py` (add `field` if missing).

In `PairedActuator` (after `require_prefix`):

```python
    # Optional per-series card-label overrides. Maps a Series-value PREFIX
    # (e.g. "5016A") to the label to show instead of `label`. Used so 5016
    # shows "A Port Close"/"B Port Close" while other series keep the generic
    # Fail-Safe labels. Prefix match against the row's Series (col 5).
    series_labels: dict = field(default_factory=dict)

    def label_for(self, series_value: str | None) -> str:
        if series_value:
            sv = str(series_value).strip()
            for prefix, lab in self.series_labels.items():
                if sv.startswith(prefix):
                    return lab
        return self.label
```

In `ValveTypeConfig` (after `extra_row_sources`):

```python
    # Optional per-series cascade field-visibility overrides. Maps a value of
    # the `cascade_override_key` field (matched by PREFIX) to the ordered list
    # of cascade keys that stay visible for that value. Fields not listed are
    # hidden and skipped in resolution. Empty = same 12 fields for every series.
    cascade_overrides: dict = field(default_factory=dict)
    # Which cascade key's value selects the override; defaults to the first
    # cascade key (Series) when cascade_overrides is set.
    cascade_override_key: str | None = None
```

- [ ] **Step 5: Set the fields on `CONTROL_VALVE`**

Add to the `CONTROL_VALVE = ValveTypeConfig(...)` call (e.g. just before `detail_columns=`):

```python
    cascade_override_key="series",
    cascade_overrides={
        "5016A": ["series", "body_material", "trim_material",
                  "characteristics", "end_connection", "face_to_face"],
        "5016B": ["series", "body_material", "trim_material",
                  "characteristics", "end_connection", "face_to_face"],
    },
```

And add `series_labels` to the two control-valve `PairedActuator` entries:

```python
    paired_actuators=(
        PairedActuator(
            model_col=46, target_field="model", target_type="pneumatic_msd",
            require_prefix="MSD-", label="Fail-Safe Close (Normally Closed)",
            series_labels={"5016A": "A Port Close", "5016B": "A Port Close"},
        ),
        PairedActuator(
            model_col=47, target_field="model", target_type="pneumatic_msd",
            require_prefix="MSD-", label="Fail-Safe Open (Normally Open)",
            series_labels={"5016A": "B Port Close", "5016B": "B Port Close"},
        ),
    ),
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd ~/repos/avconproducts && py -m pytest tests/test_cv_config.py -q`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
cd ~/repos/avconproducts
git add app/catalog.py tests/test_cv_config.py
git commit -m "feat(control-valve): add per-series cascade_overrides + actuator series_labels config"
```

---

### Task 3: Apply per-series actuator label in `resolve()` (+ mirror in engine)

**Files:**
- Modify: `app/catalog.py` `Catalog.resolve()` (~1729-1756, the `paired_actuators` loop)
- Modify: `docs/static/catalog-engine.js` `resolve()` (~171-207, the paired loop)
- Test: `tests/test_cv_resolve_label.py` (create)

**Interfaces:**
- Consumes: `PairedActuator.label_for()` (Task 2), the row's Series value at `c{series_col}` where `series_col` is the col of the `cascade_override_key` field.
- Produces: `detail["paired_actuators"][i]["label"]` reflects the per-series label; dedup key stays `(target_type, model)` so identical A/B models collapse to one card (label = first entry's per-series label).

- [ ] **Step 1: Write the failing test**

Create `tests/test_cv_resolve_label.py`. This test constructs a minimal `Catalog` around `CONTROL_VALVE` with two hand-built rows (a 5016 SKU with distinct A/B models, and one with identical A/B), bypassing Excel. First inspect the `Catalog` constructor and `_filter` in `app/catalog.py` to build rows in the `c{col}` dict shape; the row dict keys are `"c<col>"`.

```python
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from catalog import Catalog, CONTROL_VALVE  # noqa: E402

def _row(**cols):
    # cols like series=..., c46=..., etc.; returns {"c<col>": val}
    base = {f"c{c}": "" for c in range(1, 60)}
    base.update(cols)
    return base

class TestResolveLabels(unittest.TestCase):
    def _cat(self, rows):
        cat = Catalog.__new__(Catalog)      # bypass __init__/Excel load
        cat.config = CONTROL_VALVE
        cat.rows = rows
        return cat

    def test_5016_distinct_models_two_cards_with_port_labels(self):
        # series col 5, A-Port col 46, B-Port col 47; give the 6 cascade cols so
        # _filter matches. Use minimal picks that uniquely select this row.
        row = _row(**{"c2": "5016AD9001", "c3": "CAT-1", "c5": "5016A205",
                      "c7": "WCB", "c8": "SS", "c10": "On-Off",
                      "c11": "Flanged", "c14": "ISA",
                      "c46": "MSD-630 D", "c47": "MSD-430 A"})
        cat = self._cat([row])
        d = cat.resolve({"series": "5016A205", "body_material": "WCB",
                         "trim_material": "SS", "characteristics": "On-Off",
                         "end_connection": "Flanged", "face_to_face": "ISA"})
        labels = [p["label"] for p in d["paired_actuators"]]
        self.assertEqual(labels, ["A Port Close", "B Port Close"])

    def test_5016_identical_models_one_card_aport_label(self):
        row = _row(**{"c2": "5016AD9002", "c3": "CAT-2", "c5": "5016A205",
                      "c7": "WCB", "c8": "SS", "c10": "On-Off",
                      "c11": "Flanged", "c14": "ISA",
                      "c46": "MSD-630 D", "c47": "MSD-630 D"})
        cat = self._cat([row])
        d = cat.resolve({"series": "5016A205", "body_material": "WCB",
                         "trim_material": "SS", "characteristics": "On-Off",
                         "end_connection": "Flanged", "face_to_face": "ISA"})
        labels = [p["label"] for p in d["paired_actuators"]]
        self.assertEqual(labels, ["A Port Close"])

    def test_5012_keeps_generic_labels(self):
        row = _row(**{"c2": "5012AC9001", "c3": "CAT-3", "c5": "5012A205",
                      "c7": "WCB", "c8": "SS", "c10": "On-Off",
                      "c11": "Flanged", "c14": "ISA",
                      "c46": "MSD-200 C", "c47": "MSD-200 A"})
        cat = self._cat([row])
        d = cat.resolve({"series": "5012A205", "body_material": "WCB",
                         "trim_material": "SS", "characteristics": "On-Off",
                         "end_connection": "Flanged", "face_to_face": "ISA"})
        labels = [p["label"] for p in d["paired_actuators"]]
        self.assertEqual(labels, ["Fail-Safe Close (Normally Closed)",
                                  "Fail-Safe Open (Normally Open)"])
```

If `Catalog.__new__` / `_filter` needs more attributes than `config`/`rows` (e.g. an index), inspect `Catalog.__init__` and set them minimally, or add a small classmethod `Catalog.from_rows(config, rows)` used only by tests. Prefer the `__new__` approach if `_filter` only reads `self.rows`/`self.config`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/repos/avconproducts && py -m pytest tests/test_cv_resolve_label.py -q`
Expected: FAIL — labels are the generic "Fail-Safe …" strings, not "A Port Close"/"B Port Close".

- [ ] **Step 3: Apply the per-series label in `resolve()`**

In `app/catalog.py` `Catalog.resolve()`, compute the row's series value once (before the paired loop):

```python
        # Per-series actuator labels: look up the row's controlling-field value.
        _ov_key = self.config.cascade_override_key or (
            self.config.cascade[0][0] if self.config.cascade else None
        )
        _ov_col = None
        if _ov_key:
            for k, col, _lab in self.config.cascade:
                if k == _ov_key:
                    _ov_col = col
                    break
        _row_series = row.get(f"c{_ov_col}") if _ov_col else None
```

Then in the loop, replace `"label": p.label,` with:

```python
                "label": p.label_for(_row_series),
```

(Dedup logic unchanged — it keys on `(target_type, model)`, so identical A/B models still collapse to one card, taking the first entry's per-series label.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/repos/avconproducts && py -m pytest tests/test_cv_resolve_label.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Mirror in `docs/static/catalog-engine.js`**

In `resolve()` of `docs/static/catalog-engine.js`, before the paired loop, resolve the row's series value:

```javascript
    // Per-series actuator labels (mirror of catalog.py Catalog.resolve).
    const ovKey = cat.cascade_override_key ||
                  (cat.cascade[0] && cat.cascade[0].key) || null;
    let rowSeries = null;
    if (ovKey) {
      const ovCol = cat.keyToCol.get(ovKey);
      if (ovCol != null) rowSeries = row[cat.colIndex.get(ovCol)];
    }
    const labelFor = (pa) => {
      if (rowSeries && pa.series_labels) {
        const sv = String(rowSeries).trim();
        for (const prefix of Object.keys(pa.series_labels)) {
          if (sv.startsWith(prefix)) return pa.series_labels[prefix];
        }
      }
      return pa.label;
    };
```

Then in the loop where `paired.push({... label: pa.label ...})`, change to `label: labelFor(pa)`. (Verify the exact variable names `row`, `cat.colIndex`, `cat.keyToCol` against lines 80/130-195; adapt if they differ.)

- [ ] **Step 6: Commit**

```bash
cd ~/repos/avconproducts
git add app/catalog.py docs/static/catalog-engine.js tests/test_cv_resolve_label.py
git commit -m "feat(control-valve): per-series actuator card labels (A/B Port for 5016)"
```

---

### Task 4: Serialize the new config + render data attributes

**Files:**
- Modify: `tools/build_static.py` (`_serialize_catalog` ~73-108: paired dict + catalog dict; `_section_summary` ~111-125)
- Modify: `app/server.py` (`_section_summary` ~58-72)
- Modify: `app/templates/index.html` (the section wrapper that owns the picker form, near the `{% for field in section.cascade %}` loop ~178)
- Test: `tests/test_cv_serialize.py` (create)

**Interfaces:**
- Consumes: `cfg.cascade_overrides`, `cfg.cascade_override_key`, `pa.series_labels` (Task 2).
- Produces:
  - `control_valve.json` gains top-level `"cascade_overrides"` (object) and `"cascade_override_key"` (string|null); each `paired_actuators[i]` gains `"series_labels"` (object).
  - The rendered section wrapper in `index.html` carries `data-cascade-overrides='<json>'` and `data-cascade-override-key='<key>'` for `app.js` to read.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cv_serialize.py`:

```python
import os, sys, unittest, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from catalog import load_all  # noqa: E402
import build_static  # noqa: E402

class TestSerialize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogs = load_all()
        cls.cv = cls.catalogs["control_valve"]

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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/repos/avconproducts && py -m pytest tests/test_cv_serialize.py -q`
Expected: FAIL (`KeyError: 'cascade_override_key'` / `'series_labels'`).

- [ ] **Step 3: Serialize `series_labels` and overrides in `build_static.py`**

In `_serialize_catalog`, add `"series_labels"` to the paired dict:

```python
    paired = []
    for pa in cfg.paired_actuators:
        paired.append({
            "model_col": pa.model_col,
            "target_field": pa.target_field,
            "label": pa.label,
            "target_type": pa.target_type,
            "target_by_prefix": [list(t) for t in pa.target_type_by_prefix] or None,
            "require_prefix": pa.require_prefix,
            "series_labels": dict(pa.series_labels),
        })
```

And add two keys to the returned catalog dict (next to `"cascade"`):

```python
        "cascade_overrides": {k: list(v) for k, v in cfg.cascade_overrides.items()},
        "cascade_override_key": cfg.cascade_override_key,
```

In `build_static.py` `_section_summary`, add:

```python
        "cascade_overrides": {k: list(v) for k, v in cfg.cascade_overrides.items()},
        "cascade_override_key": cfg.cascade_override_key,
```

- [ ] **Step 4: Mirror in `app/server.py` `_section_summary`**

Add the same two keys to `app/server.py`'s `_section_summary` dict:

```python
        "cascade_overrides": {k: list(v) for k, v in cfg.cascade_overrides.items()},
        "cascade_override_key": cfg.cascade_override_key,
```

- [ ] **Step 5: Run the serialize test to verify it passes**

Run: `cd ~/repos/avconproducts && py -m pytest tests/test_cv_serialize.py -q`
Expected: PASS (3 tests).

- [ ] **Step 6: Render data attributes in the template**

In `app/templates/index.html`, find the element that wraps each section's picker form (the one containing `{% for field in section.cascade %}`, near line 178). On that wrapper (or the `<form class="picker">` element), add:

```html
data-cascade-overrides='{{ section.cascade_overrides | tojson }}'
data-cascade-override-key='{{ section.cascade_override_key or "" }}'
```

Keep the existing `{% for field in section.cascade %}` loop rendering all fields (superset). Each field row already has `data-field="{{ field.key }}"` (line 179) — app.js relies on this in Task 5.

- [ ] **Step 7: Commit**

```bash
cd ~/repos/avconproducts
git add tools/build_static.py app/server.py app/templates/index.html tests/test_cv_serialize.py
git commit -m "feat(build): serialize cascade_overrides + paired series_labels; render data attrs"
```

---

### Task 5: Per-series field hiding in the picker (`app/static/app.js`)

**Files:**
- Modify: `app/static/app.js` (`Picker` class: constructor ~49-73, `_currentPicks` ~94-106, `refreshOptions` ~140-154, `refreshResolution` ~156-171, `_onChange` ~349-356, `setFieldValue` ~336-347, `init` ~358-361)
- Modify: `app/static/styles.css` (add a hidden-row rule)

**Interfaces:**
- Consumes: `data-cascade-overrides` / `data-cascade-override-key` on the picker section (Task 4); each field row `.row[data-field="<key>"]` (index.html).
- Produces: when the controlling field's value matches an override prefix, only the listed field keys stay visible/active; others are hidden, cleared, and excluded from picks/options/resolution.

**Note:** There is no JS unit-test harness in this repo. This task is verified behaviorally in Task 6 (live drive). Implement carefully; the steps below are exact.

- [ ] **Step 1: Parse the override config in the constructor**

In `Picker` constructor, after `this.fieldKeys = ...` (line 54), add:

```javascript
    let ov = {}, ovKey = "";
    try { ov = JSON.parse(this.form.dataset.cascadeOverrides || this.section.dataset.cascadeOverrides || "{}"); }
    catch (_e) { ov = {}; }
    ovKey = this.form.dataset.cascadeOverrideKey || this.section.dataset.cascadeOverrideKey || "";
    this.cascadeOverrides = ov;                 // { "<seriesPrefix>": [keys...] }
    this.overrideKey = ovKey || (this.fieldKeys[0] || "");
    this.activeKeys = new Set(this.fieldKeys);  // default: all visible
```

(Read the attribute from whichever element carries it — match where Task 4 rendered it. If it's on `<form class="picker">`, `this.form.dataset` is correct.)

- [ ] **Step 2: Add `_recomputeActiveKeys()` + `_applyVisibility()`**

Add two methods to `Picker`:

```javascript
  _recomputeActiveKeys() {
    let keys = this.fieldKeys;               // default all
    if (this.overrideKey && Object.keys(this.cascadeOverrides).length) {
      const field = this.fields.find((f) => f.dataset.key === this.overrideKey);
      const val = field ? String(field.value || "").trim() : "";
      for (const prefix of Object.keys(this.cascadeOverrides)) {
        if (val && val.startsWith(prefix)) { keys = this.cascadeOverrides[prefix]; break; }
      }
    }
    this.activeKeys = new Set(keys);
  }

  _applyVisibility() {
    for (const f of this.fields) {
      const active = this.activeKeys.has(f.dataset.key);
      const rowEl = f.closest(".row");
      if (rowEl) rowEl.classList.toggle("field-hidden", !active);
      if (!active && f.value) f.value = "";   // clear hidden field's value
    }
  }
```

- [ ] **Step 3: Make picks/options/resolution respect `activeKeys`**

- In `_currentPicks()`, skip inactive fields — add at the top of the loop body:
  ```javascript
      if (!this.activeKeys.has(f.dataset.key)) continue;
  ```
- In `refreshOptions()`, skip filling inactive fields — in the `for (const f of this.fields)` loop add:
  ```javascript
      if (!this.activeKeys.has(f.dataset.key)) continue;
  ```
- In `refreshResolution()`, exclude inactive keys from `requiredKeys`:
  ```javascript
      const requiredKeys = this.fieldKeys.filter((k) => {
        if (!this.activeKeys.has(k)) return false;
        if (k in picks) return true;
        const opts = this.validOptions.get(k) || [];
        return opts.length > 0;
      });
  ```

- [ ] **Step 4: Recompute on change / init / setFieldValue**

- In `_onChange(ev)`, after resetting downstream fields and before `refreshOptions()`:
  ```javascript
      if (ev.target.dataset.key === this.overrideKey) {
        this._recomputeActiveKeys();
        this._applyVisibility();
      }
  ```
- In `setFieldValue(key, value)`, after setting the value / resetting downstream, add the same two-line recompute+apply guarded by `if (key === this.overrideKey)`.
- In `init()`, before the first `refreshOptions()`:
  ```javascript
      this._recomputeActiveKeys();
      this._applyVisibility();
  ```
- In the reset handler (`resetBtn` click, ~85-89), after clearing field values add `this._recomputeActiveKeys(); this._applyVisibility();` so reset restores the full field set.

- [ ] **Step 5: Add the hidden-row CSS**

In `app/static/styles.css`, add:

```css
/* Per-series cascade: a field hidden for the selected series (e.g. 5016
   shows only 6 of the 12 Control Valve fields). */
.row.field-hidden { display: none; }
```

- [ ] **Step 6: Commit**

```bash
cd ~/repos/avconproducts
git add app/static/app.js app/static/styles.css
git commit -m "feat(picker): per-series field visibility (5016 -> 6 fields)"
```

---

### Task 6: Build, test, deploy, and verify live

**Files:** none (build + verification only)

- [ ] **Step 1: Rebuild the static bundle**

Run: `cd ~/repos/avconproducts && PYTHONUTF8=1 py tools/build_static.py`
Expected: `wrote control_valve.json — 17,681 rows`, `copied … app.js`, `wrote index.html`, `done`.

- [ ] **Step 2: Run the full test suite**

Run: `cd ~/repos/avconproducts && PYTHONUTF8=1 py -m pytest tests/ -q`
Expected: all tests pass (the original 6 + the new tests from Tasks 1-4).

- [ ] **Step 3: Re-verify 0-ambiguous for the 6-field 5016 set**

Run:
```bash
cd ~/repos/avconproducts && PYTHONUTF8=1 py - <<'PY'
import pandas as pd
p="data/Valve/Pune/Control Valve Data Set/Control Valve Dashboard_V2.xlsx"
df=pd.read_excel(p,sheet_name="Control Valve",header=0,dtype=object)
codes=df["Bare Valve Code"].astype(str)
def cv(d,n): return d.iloc[:,n-1]
for pre in ["5016A","5016B"]:
    s=df[codes.str.startswith(pre)]
    key=list(zip(cv(s,5),cv(s,7),cv(s,8),cv(s,10),cv(s,11),cv(s,14)))
    g=pd.DataFrame({'k':key,'cat':cv(s,3).astype(str).values}).groupby('k')['cat'].nunique()
    print(pre,"ambiguous:",int((g>1).sum()))
PY
```
Expected: `5016A ambiguous: 0` and `5016B ambiguous: 0`.

- [ ] **Step 4: Drive the picker locally (Flask + browser)**

Start the dev app (`py app/server.py` or the documented run command) and open the Control Valve section. Verify:
- Select Series `5012A…` → all 12 fields visible.
- Select Series `5016A…` → only 6 fields visible (Series, Body Material, Trim Material, Characteristics, End Connections, Face to Face), in that order; the other 6 rows are hidden.
- Complete the 6 fields for a 5016 SKU with distinct A/B models → result shows **two** actuator cards labelled "A Port Close" and "B Port Close".
- Complete a 5016 SKU whose A/B models are identical → **one** card labelled "A Port Close".
- Switch Series back to `5012A…` → form re-expands to 12; a 5012 match shows "Fail-Safe Close (Normally Closed)" / "Fail-Safe Open (Normally Open)".

- [ ] **Step 5: Commit the rebuilt bundle**

```bash
cd ~/repos/avconproducts
git add docs/
git commit -m "build(control-valve): rebuild docs for 5016 per-series cascade + dual actuators"
```

- [ ] **Step 6: Push and verify live**

```bash
cd ~/repos/avconproducts && git push origin main
```
Then wait ~95s and verify:
```bash
LOCALV=$(grep -o "?v=[0-9]\{14\}" docs/index.html | head -1); echo "local: $LOCALV"
curl -s "https://codeslurp.github.io/avconproducts/index.html?cb=$(date +%s)" | grep -o "?v=[0-9]\{14\}" | head -1
curl -s "https://codeslurp.github.io/avconproducts/index.html?cb=$(date +%s)" | grep -o "data-cascade-override-key='[^']*'" | head -1
```
Expected: live build stamp equals `$LOCALV`; the `data-cascade-override-key='series'` attribute is present in the live HTML. Then hard-refresh the live site and repeat the Step-4 checks in the browser.

- [ ] **Step 7: Update DESIGN.md Appendix C + memory**

Add an Appendix C entry documenting the per-series cascade rule (5016 → 6 fields) and the 5016 "A Port Close"/"B Port Close" actuator labels, so it isn't silently reverted. Update the auto-memory `pcf-control-valve-r1-newstructure` note. Commit:

```bash
cd ~/repos/avconproducts && git add DESIGN.md && git commit -m "docs(design): record 5016 per-series cascade + A/B Port actuator labels (Appendix C)"
```

---

## Self-Review

**Spec coverage:**
- Per-series cascade (5016 → 6 fields, dynamic) → Tasks 2 (config), 4 (serialize + template), 5 (frontend hide). ✅
- Requested field order (Series, Body, Trim, Characteristics, End Connections, Face to Face) → base-order subset; asserted in Task 2 test + verified live Task 6. ✅
- Two actuator cards "A Port Close"/"B Port Close", 5016 only → Task 3 (labels) + Task 1 (restore B-Port data). ✅
- Dedup option (a) (one card when A==B) → Task 3 (dedup unchanged), tested in `test_cv_resolve_label`. ✅
- Restore B-Port from original R4 → Task 1. ✅
- Non-regression (other series, catalog.py/engine sync, 0-ambiguous, cost cols) → Global Constraints + Task 6 Steps 3-4. ✅

**Placeholder scan:** No TBD/TODO; every code step shows the code. The only "verify against current names" notes (Task 3 Step 5 engine variable names; Task 5 attribute host element) are explicit re-checks, not deferred work.

**Type consistency:** `cascade_overrides: dict`, `cascade_override_key: str|None`, `series_labels: dict`, `label_for(series_value)` used consistently across Tasks 2→3→4. JSON keys `cascade_overrides` / `cascade_override_key` / `series_labels` consistent across build_static, server, template, app.js. Field-row selector `.row[data-field=…]` matches index.html line 179.

## Notes / risks
- If `Catalog._filter` needs more than `config`+`rows` (Task 3 test), inspect `Catalog.__init__` and either set the minimal extra attributes or add a test-only `Catalog.from_rows`. Keep it minimal.
- The controlling-field value is the full Series string (`5016A205`), so override/label matching is by **prefix** everywhere (Python `startswith`, JS `startsWith`). Do not switch to exact equality.
