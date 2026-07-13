# Control Valve 5016 — per-series cascade + dual actuator cards — design

**Date:** 2026-07-12
**Author:** skarnik (with Claude)
**Status:** approved (design); pending implementation plan

## Problem

For the **5016A / 5016B** Control Valve series only, the user wants:

1. **Selection fields reduced** to six, in this order:
   `Series, Body Material, Trim Material, Characteristics, End Connections, Face to Face`.
   All other Control Valve series (5012A/B, 5061A, 5066A) keep the current
   full 12-field cascade.
2. **Two recommended-actuator cards** labelled **"A Port Close"** and
   **"B Port Close"** (instead of the generic "Fail-Safe Close (Normally
   Closed)" / "Fail-Safe Open (Normally Open)" used for other series).

Today the Control Valve cascade is a single fixed 12-field list shared by every
series (`CONTROL_VALVE.cascade` in `app/catalog.py`), and `paired_actuators`
labels are global per valve type. Per-series variation is a new capability.

### Current state (verified)
- `CONTROL_VALVE.cascade` (12 fields, `app/catalog.py:1195`):
  series(5), size(6), body_material(7), trim_material(8), seat_material(9),
  characteristics(10), flow_direction(19), end_connection(11), face_to_face(14),
  port_size(15), bonnet_type(21), certification(39).
- `paired_actuators` (`app/catalog.py:1250`): col 46 → "Fail-Safe Close (Normally
  Closed)", col 47 → "Fail-Safe Open (Normally Open)". Cards **dedup** by
  `(target_type, model)` — one card when the two models are identical.
- Dropdowns are static `<select>` elements rendered in `index.html` from
  `config.cascade`; `app.js` reads them via `querySelectorAll` and resolves
  progressively. `refreshResolution()` already treats a field with **zero**
  options as "not applicable" — but the fields we hide for 5016 have options,
  so hiding needs explicit logic.
- **Data reality:** in the shipped `Dashboard_V2`, 5016 col 46
  (`Fail Safe Close / A-Port Close`) is 100% populated with MSD models; col 47
  (`Fail Safe Open / B-Port Close`) is **blank** — AVCON removed it in the
  R4_Updated drop (ingested as-is). The **original R4 file**
  (`Control Valve Data for New Structure 5016A-B_24.12.2025_R4.xlsx`, still in
  the repo, `working` tab) retains the B-Port/"Fail Safe Open" MSD models,
  **distinct from A-Port on ~50% of SKUs** (640/1280 in 5016A, 320/640 in 5016B).

### Validation done up front
- The proposed 6-field cascade resolves 5016 to **0 ambiguous**: each 6-field
  tuple maps to exactly one Catalogue code (5016A: 320 tuples, 5016B: 320
  tuples, 0 ambiguous). The 0-ambiguous invariant holds.

## Decisions (from brainstorming)
1. **Scope:** dynamic per-series — Series stays the first dropdown; picking
   5016A/5016B collapses the form to 6 fields; other series keep 12.
2. **B-Port data:** restore the B-Port (Open) actuator column for 5016 from the
   original R4 file (reverses the "drop Open" outcome for 5016 only).
3. **Dedup:** keep existing dedup — show one card when A-Port == B-Port model,
   two when they differ (option (a)).

## Design

### 1. Per-series cascade (config + frontend; no backend logic change)

- **Config (`app/catalog.py`):** add an optional field to `ValveTypeConfig`,
  e.g.:
  ```python
  cascade_overrides: dict[str, list[str]] = {}   # series-value -> visible field keys
  ```
  On `CONTROL_VALVE`, set:
  ```python
  cascade_overrides={
      "5016A": ["series","body_material","trim_material",
                "characteristics","end_connection","face_to_face"],
      "5016B": ["series","body_material","trim_material",
                "characteristics","end_connection","face_to_face"],
  }
  ```
  The base `cascade` stays the full 12 (superset). Filtering the base order to
  the 6 keys already yields the requested order — **no reordering logic needed**.
  The override is keyed on the value of the controlling field; that field is the
  first cascade key (`series`). (Add an explicit `cascade_override_key="series"`
  for clarity/generality; default to `cascade[0].key`.)

- **Serialization (`tools/build_static.py`):** emit `cascade_overrides` (and
  `cascade_override_key`) into `control_valve.json`. `index.html` continues to
  render all 12 selects (the superset) — unchanged.

- **Frontend (`app/static/app.js`, shared by dev + deployed site):**
  - Track `this.activeKeys` (Set of visible field keys); default = all field
    keys.
  - When the controlling field (`series`) changes, look up
    `cascade_overrides[value]`; if present, `activeKeys` = that list, else all.
  - A field whose key ∉ `activeKeys` is **inactive**: add a hidden class to its
    label+control, clear its value, and skip it in `_currentPicks()`,
    `refreshOptions()`, and the `requiredKeys` computation in
    `refreshResolution()`.
  - Recompute on every controlling-field change so switching series expands/
    collapses the form and resets downstream fields (existing reset-on-change
    behavior preserved).

- **Backend (`app/catalog.py` options/resolve):** no change. It matches on the
  picks it receives; the frontend simply omits inactive fields. Resolution stays
  unique because the 6-field set is 0-ambiguous for 5016.

### 2. Dual actuator cards (A Port Close / B Port Close), 5016 only

- **Restore B-Port data (`tools/consolidate_control_valve.py`):** after building
  the 5016 frames from R4_Updated, **enrich** canonical col 47
  (`Fail Safe Open / B-Port Close`) from the original R4 file's `Fail Safe Open`
  column, joined by `Bare Valve Code`. Col 46 (A-Port) unchanged. Implement as an
  optional `enrich` list on the UPDATED_DROPS entry:
  ```python
  "enrich": [{
      "canonical": "Fail Safe Open / B-Port Close",
      "from_file": "Control Valve Data for New Structure 5016A-B_24.12.2025_R4.xlsx",
      "from_sheet": "working",
      "from_col": "Fail Safe Open",
      "key_col": "Bare Valve Code",
  }]
  ```
  Strict: abort if the source file/sheet/column is missing or any 5016 Bare Valve
  Code fails to join. Report the fill count.

- **Per-series actuator labels (`app/catalog.py` + `docs/static/catalog-engine.js`):**
  add an optional per-series label override to `PairedActuator`, e.g.
  `series_labels: dict[str, str] = {}` keyed on the Series value (col 5). In
  `Catalog.resolve()`, when building each paired-actuator card, use
  `series_labels.get(row_series, default_label)`. Mirror the identical logic in
  `catalog-engine.js` (Appendix C #2 — both must match).
  - col 46: `series_labels={"5016A":"A Port Close","5016B":"A Port Close"}`
  - col 47: `series_labels={"5016A":"B Port Close","5016B":"B Port Close"}`
  - Other series fall back to the existing "Fail-Safe Close/Open (Normally
    …)" labels.

- **Dedup:** unchanged — the existing `(target_type, model)` dedup applies, so
  when A-Port model == B-Port model (≈50% of 5016 SKUs) a single card shows;
  when they differ, both "A Port Close" and "B Port Close" show. (Option (a).)

### 3. Scope / non-regression
- Only `control_valve` is affected. 5012/5061/5066 keep the 12-field form and
  the existing actuator labels.
- Cost/pricing columns remain excluded from cascade/detail/JSON.
- The 0-ambiguous invariant is preserved (re-verify after build).
- Keep `app/catalog.py` resolve() and `docs/static/catalog-engine.js` in sync
  (Appendix C #2, #6).

## Testing / verification
- Unit: extend `tests/` — (a) 5016A/5016B options/resolve returns only the 6
  fields' constraints and resolves uniquely; (b) `cascade_overrides` absent →
  full 12 fields (no regression for 5012 etc.); (c) 5016 resolve yields two
  distinct actuator cards where A≠B and one where A==B.
- Data: consolidation report shows col 47 filled for 5016 after enrichment;
  0-ambiguous re-verified; total rows unchanged (17,681).
- Build + live: rebuild `docs/`, push, verify live build stamp + JSON
  (5016 col 47 populated, cascade_overrides present), and drive the picker
  (select 5016A → 6 fields; select 5012A → 12 fields; two actuator cards on a
  5016 SKU with distinct A/B models).

## Out of scope
- No changes to other valve types, the accessories flow, or the actuator
  catalogs themselves.
- No reordering framework beyond subset-filtering the base cascade order.
