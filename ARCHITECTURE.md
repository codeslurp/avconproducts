# AVCON Product Code Finder — Architecture & Logic

> Local Flask web app that replaces AVCON's Excel-based SKU lookup workflow
> for the sales team. The user picks a valve, sees recommended actuators,
> configures the actuator, optionally picks accessories, and gets a
> consolidated product code summary at the bottom.

**Catalog scale:** 49,289 valve + actuator SKUs across 5 product families
+ 162 accessory SKUs across 13 families.
**Distribution:** local-only — the app binds to `127.0.0.1:5037` and is
launched by double-clicking `run.bat`. No data leaves the machine.

---

## 1. Folder layout

```
Product Code Finder/
├── run.bat                                  # double-click to launch
├── build_bundle.bat                         # packages distribution ZIP
├── README.txt                               # end-user launch instructions
├── MAINTENANCE.txt                          # how engineering updates the catalog
├── AVCON_Product_Code_Finder_Overview.pptx  # leadership deck
├── ARCHITECTURE.md                          # THIS FILE
│
├── app/
│   ├── server.py                            # Flask app, route handlers
│   ├── catalog.py                           # cascade catalog system (valves + actuators)
│   ├── accessories.py                       # flat-list accessories loader
│   ├── static/
│   │   ├── app.js                           # all client-side logic
│   │   ├── styles.css                       # AVCON-branded styling
│   │   └── avcon-logo.png                   # brand asset
│   └── templates/
│       └── index.html                       # single-page Jinja template
│
├── data/
│   ├── Accessories/
│   │   └── Dashboard accessories.xlsx       # consolidated accessory dashboard
│   ├── Actuator/
│   │   ├── Actuator.xlsx                    # (legacy aggregate — unused by code)
│   │   ├── Electrical Actuator/
│   │   │   └── Electrical Actuator Rotory Data Sheet Structure - 09.12.2025.xlsx
│   │   └── Pneumatic Actuator/
│   │       ├── Rack & Pinion Data Sheet Structure new.xlsx
│   │       └── Scotch Yoke Actuator Data Sheet Structure - 08.12.2025.xlsx
│   └── Valve/
│       ├── Ball Valve Data Set/
│       │   ├── Ball Valve Data Sheet Structure NEW OG - R01.xlsm   # master (legacy)
│       │   ├── Valve_Code_Selector_Dashboard.xlsx                  # CURRENT enrichment source
│       │   └── 2030F/2060F/2070F/2090F BV NEW CODEING.xlsx        # (legacy per-series — no longer used)
│       └── Butterfly Valve Data Set/
│           ├── Butterfly Valve Centric Data Sheet Structure OG - R01 (1).xlsm  # master
│           ├── BUTTERFLY VALVE DATABASE COPY.xlsx                              # (consolidated alt — not active)
│           └── 4020B / 4022B / 4023B BFV NEW CODEING *.xlsx                    # per-series enrichment (3 files)
│
├── python/                                  # bundled Python runtime for distribution
├── tools/                                   # dev/build helper scripts
└── screenshots/                             # PNG captures used in the leadership deck
```

**File discovery is recursive.** `catalog.py:find_catalog_file` uses
`data_dir.rglob("*.xls*")` to find catalog files by filename-substring
anywhere under `data/`. This is what lets engineering rename or reorganize
subfolders without breaking the app — only filename substrings matter.

---

## 2. Data flow — overall picture

```
   Excel files in data/                         in-memory rows                        HTTP API                       UI
   ─────────────────────                        ──────────────                        ────────                       ──
   master .xlsm                  ┐
   + per-series .xlsx            ├─→  Catalog.rows (cascade-resolvable)  ─→  /api/<type>/options    ─→  Picker → cascade dropdowns
   + enrichment cols 100+        ┘                                       ─→  /api/<type>/resolve    ─→  Picker → "Your Match" + chips

   Dashboard accessories.xlsx    ─→  ACCESSORIES dict (flat list)        ─→  /api/accessories/list ─→  AccessoryBrowser → multi-select list
```

**Loading happens once at app startup.** All Excel files are read in
`server.py`'s top-level code (lines 29-34). Subsequent requests are pure
in-memory lookups — no disk I/O per request. Trade-off: changes to Excel
files require restarting the app (the user just closes the terminal and
double-clicks `run.bat` again).

---

## 3. Backend — Python/Flask

### 3.1 `catalog.py` — the cascade-resolution engine

The core abstraction is a **product family** (valve type or actuator type),
declared as a `ValveTypeConfig` dataclass. Adding a new family is a single
new config block + one line in `VALVE_TYPES` list.

#### `ValveTypeConfig` — declarative schema for one product family

```python
@dataclass(frozen=True)
class ValveTypeConfig:
    key: str                            # URL identifier, e.g. "ball"
    label: str                          # UI section title, e.g. "Ball Valve"
    category: str                       # "Valves" or "Actuators"
    subgroup: str | None                # tag inside picker menu, e.g. "Pneumatic"
    file_substring: str                 # filename substring to find catalog file
    sheet_marker: str                   # substring matching sheets WITHIN the file
    cascade: list[tuple[str, int, str]] # (form-key, 1-based col, label) — drives the dropdowns
    detail_columns: list[tuple[int, str]] # cols shown in the "All attributes" panel

    # Result-panel cards. Default = "Bare Valve Code" + "Catalogue Code" + BTO/FOS.
    primary_label / primary_col
    secondary_label / secondary_col
    show_bto_fos / bto_col

    paired_actuators: tuple[PairedActuator, ...]    # recommendation chips
    enrichment_sources: tuple[EnrichmentSource, ...] # extra cols merged in after main load
```

5 configs exist today:
- `BALL_VALVE` (key=`ball`, 3,892 rows)
- `BUTTERFLY_VALVE` (key=`butterfly`, 43,200 rows)
- `PNEUMATIC_RACK_PINION` (key=`pneumatic_rp`, 1,620 rows)
- `PNEUMATIC_SCOTCH_YOKE` (key=`pneumatic_sy`, 481 rows)
- `ELECTRICAL_ROTARY` (key=`electrical_rotary`, 96 rows)

#### `Catalog.__init__` — loads one product family at startup

1. Reads the master file matching `file_substring` (picks newest by mtime).
2. Builds `self.rows` — a list of dicts where each row is `{c1: ..., c2: ..., ...}`
   keyed by 1-based column index.
3. Applies each `EnrichmentSource` in turn — see `_apply_enrichment` below.

#### `EnrichmentSource` — cross-file column merging

Used when actuator pairing data lives in a SEPARATE file from the master
(common pattern for valves — the master holds valve attributes only,
per-series files hold actuator recommendations).

```python
@dataclass(frozen=True)
class EnrichmentSource:
    file_substring: str
    sheet_marker: str
    source_key_col: int                          # join key in source (1-based)
    master_key_col: int                          # join key in master (1-based)
    columns: tuple[tuple[int, int], ...]         # (source_col, master_dest_col) pairs
```

Example: `BALL_VALVE` enriches `Valve_Code_Selector_Dashboard.xlsx` sheet
`Ball Valve Actuator combination` cols 49-59 → master cols 100-110.
The join key is `Bare Valve Code` (col 1 in both files).

**Why cols 100-110?** The valve master file has its own meaning for cols
49-58 (in butterfly's case, "Additional Specification 1-5" + weight + cost).
Writing enriched actuator data to high-numbered "virtual" columns avoids
clobbering master data. Then `paired_actuators` references col 100+ for
the recommendation cards.

#### `PairedActuator` — the recommendation routing layer

One entry per **recommendation position** (e.g., "Pneumatic Double Acting
@ 3.5 bar"). Many entries per `ValveTypeConfig` — ball valves have 11
total (9 pneumatic + 2 electric); butterfly has 11 too.

```python
@dataclass(frozen=True)
class PairedActuator:
    model_col: int               # 1-based col where the recommended MODEL name lives
    target_field: str            # which cascade key to pre-fill on jump (always "model")
    label: str                   # chip label, e.g. "Pneumatic — Double Acting @ 3.5 bar"

    target_type: str | None                          # single-catalog target, OR ↓
    target_type_by_prefix: tuple[tuple[str, str], ...] = ()  # prefix-based routing

    def resolve_target_type(self, model: str) -> str | None:
        # If prefix-based: walk pairs, return first matching target
        # Else: return target_type
```

**Why prefix-based routing exists:** butterfly valves recommend actuators
in cols 100-108 that mix R&P (`ACT-*` prefix → `pneumatic_rp` catalog) AND
Scotch Yoke (`SYA-*` prefix → `pneumatic_sy` catalog). One column,
two possible destination catalogs, dispatch by model prefix.

#### Normalization (`_normalize_paired_model`)

Source data has format drift the source Excel files haven't fixed yet.
Two patterns observed:
1. **Missing dash:** `SYA065300DAS` should be `SYA-065300DAS` (matches SY catalog format).
2. **Missing slash:** `EA-21D` should be `EA-21/D`; `QM-150D` should be `QM-150/D` (matches electrical catalog format).

Plus we filter out `#N/A` literal strings (broken VLOOKUP cells).

These are TRANSITIONAL hacks marked with `# TRANSITIONAL` comments so they
can be removed when engineering cleans the source data.

#### `Catalog.resolve()` — the cascade-resolution method

Called when the user has filled the cascade dropdowns. Returns:
```python
{
    "match_count": int,
    "fields": [{"label", "value"}, ...],           # all detail columns
    "primary": str,                                # Bare Valve Code (or Actuator Code)
    "secondary": str,                              # Catalogue Code (or Model)
    "bto" / "fos": optional (valves only),
    "paired_actuators": [                          # recommendation chips (valves only)
        {"model", "target_type", "target_field", "label"},
        ...
    ]
}
```

**Recommendation dedup:** if multiple `PairedActuator` positions all
recommend the same model (e.g., DA1=DA2=DA3=ACT-050D), the resolve method
dedupes by `(target_type, model)` so the UI sees one chip instead of three.

### 3.2 `accessories.py` — flat-list loader (no cascade)

Accessories are intentionally NOT a cascade-resolution catalog. The source
file is a "dashboard" Excel with 14 different product families stacked into
ONE sheet, each with its own column schema embedded as a header row.
There's no single set of cascade dropdowns that makes sense across all
families.

`load_accessories(data_dir)` returns:
```python
{
    "rows": [{"code", "family", "attrs": [{"label", "value"}, ...]}, ...],
    "families": [{"name", "count"}, ...],
    "headers": [...],
    "source_file": "Dashboard accessories.xlsx"
}
```

**Source-data filtering** (cheap to keep, removable when engineering cleans):
1. Skip rows where `family` starts with `Table_` — these are leaked rows
   from another catalog (e.g., `Table_2090F BV NEW CODEING` is ball-valve
   data accidentally pasted in).
2. Skip rows where `code == "Code"` (literal string) — each family's first
   row is its own column-header row that got captured as data.
3. Skip rows with no code (visual spacer rows in the dashboard layout).

Today: source has 341 rows, 162 are real SKUs after filtering.

### 3.3 `server.py` — Flask routes

```
GET  /                            → index.html (renders sections + accessories summary)
GET  /api/<valve_type>/options    → cascade options for the currently-picked fields
GET  /api/<valve_type>/resolve    → resolved SKU + recommendations (one row)
GET  /api/accessories/list        → all 162 accessory rows + families
GET  /api/health                  → loaded catalogs + row counts (smoke test)
```

`api_resolve` also enriches each `paired_actuator` entry with:
- `name` — looked up from the destination actuator catalog's Actuator + Type
  detail columns ("Pneumatic Rack & Pinion Actuator — Double Acting…").
- `not_in_catalog: true` — flagged when the recommended model isn't in the
  destination catalog (data gap, e.g., `QM-3000-10+WG60/D` doesn't exist in
  the electrical catalog yet).

Production mode: `debug=False, use_reloader=False`. Templates and Python
code are cached. **Any edit to `*.py` or `*.html` requires a server
restart.** Static JS/CSS are served fresh per request, so a browser
hard-refresh picks up those changes.

---

## 4. Frontend — HTML/CSS/JS

### 4.1 Layout (CSS Grid via `index.html` + `styles.css`)

```
┌────────────────────────────────────────────────────────────────────┐
│  Header: title (left)                              [AVCON logo]    │
├────────────────────────────────────────────────────────────────────┤
│  [VALVES dropdown]    [ACTUATORS dropdown]                         │
├──────────────────────────────┬─────────────────────────────────────┤
│  │ ◐ Valves                  │  │ ◑ Actuators                     │
│    (cascade form + result)   │    (cascade form + result)          │
├──────────────────────────────┴─────────────────────────────────────┤
│  │ + Accessories                          162 items · 13 families  │
│    [ACCESSORIES filter]   [Search]                    [X selected] │
│    (grouped multi-select list)                                      │
├────────────────────────────────────────────────────────────────────┤
│  ★ YOUR PRODUCT CODE IS                                            │
│  [VALVE card]  [ACTUATOR card]  [ACCESSORIES chips]                │
└────────────────────────────────────────────────────────────────────┘
```

Grid template areas: `"valves actuators" / "access access" / "summary summary"`.
At <980px width, all four areas collapse to a single column.

### 4.2 `app.js` — client-side classes

#### `Picker` (instances: 5 — one per `valve-section`)

- Wires up the cascade form (selects + typeahead inputs)
- On change: calls `/api/options` to refresh downstream options, then
  `/api/resolve` to fetch the SKU when the cascade is complete
- Renders the result panel (codes + paired-actuator chips + details table)
- Emits `valve-selector:resolved` / `valve-selector:cleared` events for the
  SummaryPanel to listen to

#### `TypePicker` (instances: 2 — Valves, Actuators)

The top-of-page dropdown buttons. Each shows/hides one product family's
`valve-section` when an option is picked. Independent — picking a valve
type and picking an actuator type don't interact.

#### `viewMatchingActuator(targetType, targetField, value)` (module-level fn)

Triggered when the user clicks a recommendation chip. It:
1. Opens the target Actuator family via `TypePicker.select()`
2. Pre-fills the `model` cascade field via `Picker.setFieldValue()`
3. Scrolls the actuator section into view

This is the bridge between valve and actuator cascades.

#### `Picker._renderPairedActuators` — the recommendation chip section

Groups paired-actuator entries by category (Pneumatic / Electric) under
"Option 1 / Option 2" sub-headers. Each entry renders as a small clickable
chip showing **code on top + position label below** (e.g. "ACT-050D" /
"Double Acting @ 3.5 bar"). Unavailable models (`not_in_catalog: true`)
render disabled, italic, amber.

Single `<h3>RECOMMENDED ACTUATOR</h3>` heading for the whole section — no
per-card headers (cleaner than the previous per-card "Recommended Actuator"
text repetition).

#### `AccessoryBrowser`

Manages the accessories card:
- Fetches `/api/accessories/list` once on load
- Renders rows grouped by family, with checkboxes
- Family filter dropdown (styled to match the type-picker box shape)
- Free-text search across code + family + attributes
- **One-per-family selection constraint:** when user picks a new accessory
  from family X, any previously-selected accessory in family X is
  automatically deselected. Not mandatory — user can skip families entirely.
  See `_deselectSameFamily()`.
- Broadcasts `accessories:selected-changed` with the current selection rows

#### `SummaryPanel` (one instance)

Listens for `valve-selector:resolved` and renders the Valve + Actuator
cards in the bottom summary panel. Cards stay visible after a section
hides; the panel resets only on explicit cascade reset / no-match.

#### `AccessorySummary` (one instance)

Listens for `accessories:selected-changed` and renders selected
accessories as pill chips with **family tag** (small solid-teal badge) +
**code** (monospace) in the summary panel.

---

## 5. Key UX flows

### 5.1 Pick a valve → get a product code

1. User clicks **VALVES** dropdown → picks "Ball Valve"
2. Ball Valve section appears in the Valves column
3. User fills the 8-field cascade (Series → Size → Body Mat → Ball Mat →
   Seat Mat → Characteristics → End Connection → Ball Type)
4. After each pick, downstream dropdowns refresh via `/api/options`
5. When the last field is picked, `/api/resolve` returns the SKU
6. Result panel shows: Bare Valve Code, Catalogue Code, BTO, FOS
7. Recommendation chips render below: pneumatic + electric options
8. Summary panel at the bottom of the page populates with the valve card

### 5.2 Click a recommended actuator → cascade & get its code

1. User clicks e.g. **ACT-050D** chip on a valve result
2. `viewMatchingActuator("pneumatic_rp", "model", "ACT-050D")` fires
3. Actuators column opens to the R&P section with Model pre-filled
4. User picks Body Material, Shaft Female, O-Ring Material
5. R&P resolves → shows actuator Code (e.g. `RPAD0501`) + Model + full attrs
6. Summary panel adds the Actuator card

### 5.3 Add accessories

1. User scrolls to Accessories section
2. Optionally filters by family or searches
3. Checks accessories. **Constraint:** picking a second from the same
   family auto-deselects the first.
4. Each checked accessory becomes a teal pill chip in the bottom summary
   "Accessories (N)" card, showing family + code.

### 5.4 Final state: "Your Product Code is" panel

Always at the very bottom. Shows what the user has assembled:
- Valve card (code + family name)
- Actuator card (code + model + actuator family)
- Accessories card (chips with family tag + code)

Hidden until at least one of the three has a selection.

---

## 6. Known data quirks & engineering items

The app handles these defensively; cleaning the source removes the need
for code workarounds.

| # | Issue | Affected | App's handling | Engineering fix |
|---|---|---|---|---|
| 1 | Pneumatic recommendations mix R&P + SY | 2,700 butterfly rows | Prefix-based routing in `PairedActuator` | None (data is correct) |
| 2 | `SYA065300DAS` (no dash) vs `SYA-065300DAS` (catalog format) | ~2,700 rows | `_normalize_paired_model` inserts dash | Normalize source |
| 3 | `EA-21D` / `QM-150D` (no slash) vs `EA-21/D` / `QM-150/D` | ~1,800 rows | `_normalize_paired_model` inserts slash | Normalize source |
| 4 | `#N/A` literal in cells | 196 rows | Filtered out at resolve time | Fix VLOOKUP formulas |
| 5 | Missing electric models: `QM-1000/D`, `QM-1500/D`, `QM-3000-10+WG60/D`, `QM-3000-20+WG60/D` | rows recommending these | UI shows "Data Not Available" amber state | Add rows to electrical catalog |
| 6 | Butterfly `4020M / 4022M / 4023M BON` variants have no per-series files | 21,600 of 43,200 butterfly rows | No recommendation rendered (gracefully empty) | Produce 3 new per-series files |
| 7 | Accessories file has 14 leaked `Table_*` garbage rows + 12 header-row pollution + 150 spacer rows | source-only | `accessories.py` filters all three categories | Clean source dashboard file |
| 8 | Source column-header typos (`Presssure`, `Tempreture`, `Diaphram`) | display only | Surfaced verbatim (no silent correction) | Fix headers in Excel |

---

## 7. How to extend the app

### Add a new valve or actuator family

1. **Add a `ValveTypeConfig`** block in `catalog.py` with appropriate
   `key`, `file_substring`, `sheet_marker`, `cascade`, `detail_columns`.
2. **Add it to `VALVE_TYPES`** list at the bottom.
3. **Place the Excel file** anywhere under `data/` — the recursive `rglob`
   finds it as long as the filename contains the `file_substring`.
4. Restart the server. UI auto-renders the new section.

### Add a new enrichment source

Append an `EnrichmentSource` entry to the family's `enrichment_sources`
tuple. Specify file substring, sheet marker, key columns, and the
(source_col → master_col) column mapping. No JS or HTML changes needed.

### Add a new paired-actuator position

Append a `PairedActuator` to the family's `paired_actuators` tuple. The
chip will appear in the recommendation panel. Dedup by `(target_type, model)`
will hide duplicate suggestions automatically.

### Add a new accessory family

Currently zero config — the accessories loader auto-discovers families from
column 1 of the source sheet. Just edit `Dashboard accessories.xlsx`.

### Add a new recommendation prefix → catalog routing

Edit the relevant `PairedActuator.target_type_by_prefix` tuple, adding
`(new_prefix, new_target_catalog_key)`. Tuples are checked in order; first
match wins.

### Add a new model normalization

Edit `_normalize_paired_model` in `catalog.py`. The function is small and
documented; add a new regex pattern or prefix-handling rule.

---

## 8. Operational notes

- **No persistent state.** Selections live only in the browser tab.
  Closing the tab loses them. Could be added via `localStorage` later.
- **No authentication.** The app binds to `127.0.0.1` only — accessible
  from the local machine only. Distribution model assumes single-user
  laptops.
- **Bundled Python (`python/` folder)** is used by `run.bat` so end users
  don't need to install Python. Add to a ZIP via `build_bundle.bat` for
  distribution.
- **Catalog file changes require a server restart.** Excel files are read
  once at app startup; subsequent requests are pure memory lookups.
  Engineering updates the Excel files → user closes terminal → user
  double-clicks `run.bat` again. Takes ~15 seconds.

---

## 9. File-size & startup-time profile

| Catalog | Source file size | Load time | Rows in memory |
|---|---|---|---|
| Ball Valve | 1.4 MB master + 3.2 MB dashboard | ~3-4s (master) + ~1s (enrichment) | 3,892 |
| Butterfly | 12.8 MB master + 8 MB per-series | ~6-8s (master) + ~3s (3 enrichments) | 43,200 |
| Pneumatic R&P | 0.6 MB | ~1s | 1,620 |
| Pneumatic Scotch Yoke | 0.3 MB | ~0.5s | 481 |
| Electrical Rotary | 36 KB | <0.5s | 96 |
| Accessories | 55 KB | <0.5s | 162 |

**Total startup time:** ~14 seconds on a modern laptop. Most of it is
butterfly catalog loading. After startup, all queries are sub-millisecond.

---

## 10. Why the design choices

- **Cascade dropdowns over free-text search:** the sales team is configuring
  to a real catalog, not searching unstructured text. Cascade narrows to
  exactly one SKU (or signals dead-end at the right step), with no possibility
  of typos producing invalid combinations.
- **One Python class per product family (`ValveTypeConfig`)** instead of one
  table per family in a DB: AVCON's source of truth is Excel files maintained
  by engineering. Each config block matches one file. Engineering owns the
  data, the app owns the schema mapping — clean separation.
- **Accessories as a flat list, not a cascade:** the source dashboard has 14
  different families with 14 different column schemas. Cascade-by-family
  wouldn't work (each family has its own attributes). Multi-select with
  family grouping matches how the data is actually structured AND how the
  user thinks about it ("I need an ALR, a bracket, a limit switch box").
- **One-per-family accessory constraint:** a single valve+actuator config
  needs ONE filter regulator, ONE limit switch box, ONE manual override.
  Engineering reality, encoded in the UI.
- **Recommendation chips as the bridge between valve and actuator cascades:**
  the engineering decision ("which actuator goes with this valve") is
  pre-computed in the source data. The cascade selection ("which variant")
  stays with the user. The chip click is one tap to inherit the engineering
  decision while preserving customer choice.
- **Pressure-rated labels for ball valves:** the source data carries
  "Double Acting Actuator 3.5 bar / 4 bar / 5.5 bar" column headers,
  giving the salesperson actionable context about WHY there are multiple
  options to pick from. Butterfly source data uses generic "Actuator 1/2/3"
  labels — same UI shape, less informative until engineering enriches.
