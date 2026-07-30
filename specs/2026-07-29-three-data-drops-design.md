# Design — three data drops (2026-07-29)

**Date:** 2026-07-29
**Branch:** `feat/2026-07-29-data-drops`
**Baseline commit:** `94eb04b` (main, clean)

Three files were dropped into the OneDrive data folder on 2026-07-29:

| Slot | File | Verified contents |
| --- | --- | --- |
| Valve | `Valve/Pune/Ball Valve Data Set/Ball Valve Data Sheet Structure 2094F TMBV_R03.xlsx` | sheet `2094F TMBV NEW CODEING`, 168 rows, 168 unique bare codes |
| Accessory | `Accessories/Gear Box Data for New Structure_R1.xlsx` | sheet `MHG`, 18 rows, codes `MGS*` |
| Accessory | `Accessories/Manual Override Data for New Structure_R1_Updated.xlsx` | sheet `MOR`, 13 rows, codes `MRS*` |

All figures in this document come from a single `openpyxl` read of each file
performed on 2026-07-29 against the OneDrive copies. Existing-catalog figures
come from the same read of the repo `data/` tree at commit `94eb04b`.

## Decisions (agreed with user before writing)

1. **MOR merges** to 36 SKUs — the new file is a third vendor, not a revision.
2. **Gear Box merges** into the existing `Gear Box (MHG)` manual-actuator catalog
   (59 rows), not a new accessory family.
3. **2094F becomes its own type**, `Pune > Ball Valve > Trunnion Mounted`,
   sibling to Metal and Plastic.
4. **Missing data is omitted, with a short note** — no blank or "data pending"
   widgets in the primary result panel.

---

## 1. Manual Override: 23 -> 36 SKUs

### Problem

`EXTRA_ACCESSORY_SOURCES` in `app/accessories.py` has one entry with
`file_substring: "Manual Override"`. `_load_extra_family` collects every matching
file, sorts by mtime descending, and **returns only the first**
(`app/accessories.py:228-235`). Both MOR files match that substring, so the newly
dropped file wins and the 23 existing SKUs vanish. The loader logs a cheerful
`loaded 13 MOR rows` — no error, no warning. This is the same class of silent
failure already guarded against for the THW sheet rename
(`app/accessories.py:69-75`).

### Verified data

Zero code overlap between the two files. Headers are identical (15 columns).

| File | Rows | Make | Code prefix |
| --- | --- | --- | --- |
| `..._R1.xlsx` | 13 | Q-Tork | `MRQ*` |
| `..._R1.xlsx` | 10 | Transtork | `MRT*` |
| `..._R1_Updated.xlsx` | 13 | Torque Transmissioin (Shakti) | `MRS*` |

The `MR` + vendor-letter convention (`Q` / `T` / `S`) confirms the three ranges
are intended to coexist.

### Change

Add an opt-in `merge_all: True` key to the `Manual Override` entry only. When
present, `_load_extra_family` iterates **all** matching files in ascending mtime
order and accumulates rows into an `OrderedDict` keyed by code.

- **Ordering:** oldest file first, so the existing MRQ/MRT sequence is unchanged
  and MRS appends at the end. No churn to the current picker order.
- **Duplicate codes:** later file wins. Today this path is never exercised
  (overlap is empty), but it gives correct supersede semantics if a future
  revision genuinely restates a code.
- **Logging:** print per-file row counts, the merged total, and an explicit line
  naming every code that was overridden by a later file. This is what makes the
  silent-drop failure mode impossible to repeat unnoticed.

No change is needed to `_extra_filenames()` — it already loops every file in the
folder and adds every substring match, so both MOR filenames are correctly
excluded from the consolidated-sheet search.

### Result

MOR family = **36 rows** (13 Q-Tork + 10 Transtork + 13 Shakti).

---

## 2. Gear Box: 41 -> 59 rows

### Verified data

The dropped file is schema-identical to the existing manual-actuator source —
the same 14 column headers in the same order.

| File | Rows | Make | Codes | Models |
| --- | --- | --- | --- | --- |
| `Actuator/Manual Actuator/MHG Manual Gear Box Data for New Structure_R1.xlsx` | 41 | Transtork, Q-tork | `MGT*` | `WGX-*` |
| `Accessories/Gear Box Data for New Structure_R1.xlsx` | 18 | Torque Transmissioin (Shakti) | `MGS*` | `SE-*` |

Zero code overlap. On the merged 59 rows, the existing
`make -> torque -> model` cascade resolves with **0 ambiguous combinations**.

### Change

Add one `ExtraRowSource` to `MANUAL_GEARBOX` (`app/catalog.py:1306`), mapping
source columns 1-9 to catalog columns 1-9 (1:1).

**Required guard:** `file_substring="Gear Box Data for New Structure"` also
matches the *existing* `MHG Manual Gear Box Data for New Structure_R1.xlsx`. If
`find_catalog_file` picked that file instead, dedup-by-key would add zero rows
and report nothing. The source is therefore pinned with
`path_contains="Accessories"`, which `_apply_extra_rows` supports
(`app/catalog.py:1533-1537`).

The file is read **in place**. Nothing is moved out of the drop folder.

### Result

`Gear Box (MHG)` = **59 rows**, three makes in the cascade.

---

## 3. New type: Pune > Ball Valve > Trunnion Mounted

### Verified data

- Sheet `2094F TMBV NEW CODEING`, **168 rows, 168 unique bare codes**
  (`2094FN0001` onward).
- Four sub-series: `2094F1505`, `2094F2005`, `2094F2505`, `2094F3005`.
- Sizes 6" / 8" / 10" / 12"; `ASME Class 150` and `ASME Class 300`.
- `Valve Type` (col 11) is uniform: `Ball Valve, Trunnion Mounted, Soft Seated`.
- **Not present in the metal master.** `Ball Valve Data Sheet Structure NEW OG -
  R01.xlsm` contains only `2030F`, `2060F`, `2070F`, `2090F` series sheets.
- Columns **1-48 are header-identical** to the master series sheets.
- Columns 49-58 carry different headers (`Additional Specification 1 @3.5` ...
  `Offer Rate (INR)`) where the master has the nine actuator columns, and are
  **empty in all 168 rows**.

### Empty columns (0/168 populated)

`37 Product Group`, `39 BTO`, `40 ETO`, `41 BTC`, `42 ETC`, `43 Run`,
`44 Top PCD`, `45 Stem Shape`, `46 Stem Dimension`, `47 Stem Orientation`,
`48 Stem Potrution (mm)`.

Consequence: no torque/FOS calculation and no recommended-actuator data for this
series.

### Config

New `BALL_VALVE_TRUNNION` in `app/catalog.py`, appended to `VALVE_TYPES`.

| Setting | Value |
| --- | --- |
| `key` | `ball_trunnion` |
| `label` | `Trunnion Mounted` |
| `category` / `group` / `subgroup` | `Valves` / `Pune` / `Ball Valve` |
| `file_substring` | `Ball Valve Data Sheet Structure 2094F TMBV` |
| `path_contains` | `Pune` |
| `sheet_marker` | `2094F TMBV NEW CODEING` |
| `show_bto_fos` | `False` |
| `paired_actuators` | none |
| `enrichment_sources` | none |

`file_substring` is unambiguous: the metal master is matched by `NEW OG` and the
plastic file by `Ball Valve Plastic`, so no config can hijack another's file.
This mirrors the reasoning already recorded at `app/catalog.py:211-218`.

### Cascade

Reuse the Metal 8-field cascade unchanged:
`series (4)`, `size (5)`, `body_material (6)`, `ball_material (7)`,
`seat_material (8)`, `characteristics (9)`, `end_connection (10)`,
`ball_type (22)`.

Verified against all 168 rows: **0 ambiguous, max 1 duplicate**. The data
factorizes exactly as 4 series x 3 body materials x 7 seat materials x 2 end
connections = 168, with size determined by series.

Three of the eight fields are single-valued in R03 (`Ball Material` =
`ASTM A351 Gr. CF8M`, `Characteristics` = `ONF`, `Ball Type` = `Solid Ball`).
They are kept rather than trimmed because `app/static/app.js:592` already
auto-fills single-option fields, so they cost the user no clicks, and the
cascade stays correct if a later revision introduces variety.

### Detail columns

Columns **1-11, 13-36, and 38**. That is, the master's detail set minus:

- the 11 always-empty columns listed above (37, 39-48),
- columns 49-60 (empty, and not the master's actuator layout),
- **column 12 `Design Standard`** — see the defect in section 4.

### Pending note

`ValveTypeConfig` gains an optional field:

```python
pending_note: str | None = None
```

For this type: `"Torque, actuator sizing, and design standard pending — R03 data."`

It must be added to `_serialize_catalog` in `tools/build_static.py`, which
enumerates payload fields explicitly (`tools/build_static.py:92-111`) and will
not pass a new field through on its own. The result panel renders it as a single
line where the FOS card would otherwise sit. When R04 populates the columns, the
note is removed and the columns are added back — no structural change.

### Icon

`DESIGN.md` Appendix C rule 5 requires every type to have its own icon. Add a
branch to the `item.key` chain in `app/templates/index.html:53` — a circle with
top and bottom trunnion stubs, distinguishing it from Metal's circle-and-ball.

---

## 4. Source-data defect: `Design Standard` autofill corruption

Column 12 of the 2094F sheet is corrupted by an Excel autofill drag. Every one
of the 168 rows reads:

```
ASME B16.34, API 6D, BS EN ISO 17292, ASME VIII Div. 1, EN12516- 1 & N
```

where `N` runs **2, 3, 4 ... 169** — strictly increasing, one per row. The string
is otherwise byte-identical across all rows. The master's `2090F` sheet has
exactly **1 distinct** value in the same column
(`ASME B16.34, API 6D, BS EN ISO 17292`).

**Handling:** the column is omitted from `detail_columns` for this type and
covered by the pending note. It is *not* normalized in code, because the correct
value cannot be determined from the available sources — the base string could
plausibly be the `& 2` variant or the master's shorter form, and picking one
would be an invention rather than a reading. Omitting displays nothing wrong and
invents nothing.

An engineering follow-up is written to
`docs/engineering-followups/2026-07-29-2094f-trunnion-data-gaps.md`, following
the existing pattern of `2026-06-02-rotary-actuator-code-issues.md`. It records
the autofill corruption and the 11 unpopulated columns, and asks for both in R04.

## 5. Source-data observation: vendor name misspelling

Both new files spell the make as `Torque Transmissioin (Shakti)` —
`Transmissioin` is misspelled. This string becomes a visible option in the Gear
Box `Make` dropdown.

**Handling:** loaded verbatim. A code-side correction would silently desync the
app from its source file and would be re-broken by the next data drop. The
misspelling is recorded in the same engineering follow-up for correction at
source. (Related: the existing MHG file spells the same vendor `Q-tork` while
the MOR file uses `Q-Tork`; noted, not changed.)

---

## 6. Testing

Added to the existing test suite:

| Test | Assertion |
| --- | --- |
| MOR merge | family loads **36** rows; all three prefixes `MRQ`/`MRT`/`MRS` present |
| MOR override log | a synthetic duplicate code across two files is logged, not dropped silently |
| Gear Box merge | `manual_gearbox` loads **59** rows; `make -> torque -> model` yields 0 ambiguous |
| Trunnion load | `ball_trunnion` loads **168** rows, 168 unique codes |
| Trunnion cascade | 8-field cascade yields 0 ambiguous across all rows |
| Trunnion panel | `show_bto_fos is False`, `paired_actuators == ()`, col 12 absent from `detail_columns` |
| **Metal regression** | metal ball valve row count unchanged from baseline |

The metal regression test is the one that matters most — 3,800+ existing SKUs
must be provably untouched by this work.

## 7. Deploy

`CATALOG_KEYS` in `docs/static/catalog-engine.js:31` is a **dead constant** —
declared once and referenced nowhere in `docs/` or `app/`. Types are discovered
from the per-type JSON that `tools/build_static.py` generates by iterating
`VALVE_TYPES`, and `docs/index.html` is fully pre-rendered from the Jinja
template. Adding a type therefore needs **no hand-edit to `catalog-engine.js`**;
only the icon branch in `app/templates/index.html`.

Sequence, per the project's deploy-and-verify workflow:

1. Run the Flask app locally; confirm all three changes in the UI.
2. `py tools/build_static.py`.
3. Commit and push the branch; merge to `main`.
4. Wait ~95 s for GitHub Pages to rebuild.
5. Verify **live bytes** with a cache-busted fetch, then hard-refresh in a browser.

## 8. Out of scope

- Moving the two accessory-folder files to their schema-appropriate directories.
  They are read in place.
- Any change to the Metal or Plastic ball valve configs.
- Correcting the source workbooks. Defects are reported, not patched.
- Rebuilding recommended-actuator support for 2094F. That needs R04 data.
