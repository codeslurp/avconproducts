# Control Valve R1 catalog replacement — design

**Date:** 2026-06-08
**Author:** skarnik (with Claude)
**Status:** approved (design); pending implementation plan

## Problem

AVCON delivered a revised "New Structure" R1 data set for the Pune **Control Valve**
catalog. It must fully replace the current source (`Control Valve Dashboard_V1.xlsx`)
and ship to the live PCF site.

### Source files (data-drop, OneDrive)
`OneDrive - Tesla/Desktop/personalProjects/Product Code Finder/data/Valve/Pune/Control Valve Data Set/`
- `Control Valve Data for New Structure_5012A-B-R1.xlsx`  — sheets `5012A CV `, `5012B CV`
- `Control Valve Data for New Structure 5016A-B_24.12.2025_R1.xlsx` — sheets `5016A CV `, `5016B CV`
- `Control Valve Data for New Structure_5061A-01.01.26_R1.xlsx` — sheet `5061A CV `
- `Control Valve Data for New Structure 5066A 3W BELLOW SEAL_R1.xlsx` — sheet `5066A CV `

### What changed (verified by cell-level diff, not assumed)
Diff of old `Dashboard_V1` vs new files, per overlapping bare valve code:
- **Bare Valve Codes**: stable primary key. Old series are fully retained; some series add SKUs.
- **Catalogue code**: changed in every row — restructured format
  (e.g. `5061AC0001`: `…/WCB/S41/S41/MTM/ONF/A1` → `…/WCB/S41/CA40/ONF/A1`). This *is* the "New Structure".
- **Spec columns**: Thrust, Torque, Mounting PCD, Stem Diameter, Product Group, all 10
  Additional Specs, Bare Valve Weight, Seat Material (360 rows), Valve Paint (1296 rows) — all revised.
- **Pricing**: BOM / Manufacturing / Sale / Offer rates revised in every row.
- **Columns**: same set; minor count variance between files (5012 files = 59 cols, 5016/5066 = 58).

### Row-count map (bare codes; new vs old Dashboard_V1)
| Series | Old | New | Net | Note |
|---|---|---|---|---|
| 5012A | 10,800 | 10,800 | 0 | revised in place |
| 5012B | 2,160 | 2,160 | +1* | revised; *verify (header vs real SKU) |
| 5061A | 2,160 | 2,160 | 0 | revised in place |
| 5016A | 641 | 1,280 | +639 | revised + expanded |
| 5016B | 320 | 640 | +320 | revised + expanded |
| 5066A | 320 | 640 | +320 | revised + expanded |
| **Total** | ~16,401 | ~17,681 | +~1,280 | |

## Decisions (from user)
1. **Full replace, archive old** — `Dashboard_V1` retained in an `archive/` subfolder, not deleted.
2. **Ship to prod** — repo edit → build → push → wait for Pages → verify live.
3. **Pricing: match current behavior** — already excluded from cascade and JSON
   (`CONTROL_VALVE` comment: "cost/pricing columns (56-59) deliberately excluded … never reach the public JSON").
4. **Approach A** — consolidate new files into the existing reader's shape; engine code untouched.

## Why Approach A (consolidation, not loader rewrite)

The `CONTROL_VALVE` loader (`app/catalog.py:935`) addresses columns **by position**, assuming
the `Dashboard_V1` Power-Query layout (table-name column at c1, Bare Code at c2). The new files
have no name column and a different column order. Approach A normalizes the new data into that
exact positional shape, so:
- The proven, deployed loader and `catalog-engine.js` are unchanged → minimal regression risk to
  Ball / Butterfly / Pharma valves (which share the loader).
- The new-structure handling is isolated in one repeatable prep step (reusable for future R-drops).
- Cost columns stay auto-excluded; no pricing leak.

Rejected: **B** (rewire the live positional loader — invasive, fights per-file column variance);
**C** (hand-build the file — not repeatable, error-prone across ~17.7k rows).

## Design

### Components
1. **`tools/consolidate_control_valve.py`** (new, in repo)
   - Input: the 4 R1 files (in repo `data/Valve/Pune/Control Valve Data Set/`).
   - For each of the 6 CV sheets: read with header row; reindex columns to the **canonical
     `Dashboard_V1` column order, matched by header name**; reconcile the 58/59-col variance
     against the canonical set (missing → blank column at the right position).
   - Prepend a table-name column (`"<series> CV "`) so the engine's `+1` positional offset holds.
   - Concatenate all 6 series into one sheet named `Control Valve`.
   - Write `Control Valve Dashboard_V2.xlsx`.
   - **Strict validation report** (chosen): per-series added/removed bare codes enumerated;
     5012B +1 delta resolved explicitly; column-alignment table printed; **fail loudly** on any
     header that can't be placed in the canonical order.

2. **Data placement**
   - Copy the 4 R1 files OneDrive-drop → repo `data/Valve/Pune/Control Valve Data Set/`.
   - Move `Control Valve Dashboard_V1.xlsx` → `…/Control Valve Data Set/archive/`.
   - Result: the only file matching `file_substring="Control Valve Dashboard"` in the active
     data dir is `…_V2.xlsx`. (Confirm `archive/` is excluded from the loader's scan, or that
     "_V2" is unambiguously the latest match.)

### Data flow
4 R1 files → `consolidate_control_valve.py` → `Control Valve Dashboard_V2.xlsx`
→ `tools/build_static.py` (`load_all(DATA_DIR)` via `app/catalog.py`) → `docs/data/control_valve.json` (cache-busted)
→ GitHub Pages → live PCF.

### Engine config
**No change.** `file_substring="Control Valve Dashboard"` matches `_V2`; all numeric
cascade/detail indices remain valid because consolidation preserves positions.
`catalog-engine.js` has no control-valve code (verified: `grep "control" docs/static/*.js` = empty)
— control valve is data-driven via `control_valve.json`.

### Error handling
- Prep script aborts (non-zero exit, no file written) if any source header has no canonical position,
  or if a series' row count deviates from the expected map beyond the known expansions.
- Archive collision check before moving V1.

## Verification (before claiming done)
1. **Ingest**: run Flask loader on V2 — catalogue cascade resolves with **0 ambiguous** (current
   baseline); total ≈17.7k rows; cost columns absent from output; spot-check `5061AC0001`
   → catalogue `5061A155/WCB/S41/CA40/ONF/A1`.
2. **Build**: `py tools/build_static.py` regenerates `docs/data/control_valve.json`; diff confirms
   row growth + new catalogue strings; no cost fields present.
3. **Live**: commit on branch → push → wait ~95s → `curl` live `control_valve.json` with cache-bust
   param to confirm new bytes; browser check that a control-valve code resolves with new
   catalogue/specs; hard-refresh.

## Rollback
`Dashboard_V1.xlsx` preserved in `archive/`; restoring it + rebuild reverts the catalog.
Git revert of the data/JSON commit reverts the live site.

## Out of scope (YAGNI)
No UI/icon changes; no accessory/actuator changes; no pricing exposure; no changes to other
valve families; no loader-engine edits.
