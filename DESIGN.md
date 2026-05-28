# AVCON Product Code Finder — Complete UI Replication Guide

> Everything needed to recreate this UI on another machine: dependencies,
> file inventory, exact pixel measurements, complete CSS, complete HTML,
> JS module structure, microcopy, assets. If a value isn't in this doc,
> consult the linked source file.

**Authoritative source of truth:** the actual files at [app/](app/). This
doc captures their state as of the 2026-05-27 build.

---

## Table of Contents

1. [Quick-start: replicate in 5 steps](#1-quick-start-replicate-in-5-steps)
2. [Full file inventory](#2-full-file-inventory)
3. [Dependencies & setup](#3-dependencies--setup)
4. [Logo asset specification](#4-logo-asset-specification)
5. [Font specification](#5-font-specification)
6. [Design tokens (`:root` CSS variables)](#6-design-tokens-root-css-variables)
7. [Typography scale](#7-typography-scale)
8. [Layout structure](#8-layout-structure)
9. [Complete HTML template](#9-complete-html-template)
10. [Complete CSS by section](#10-complete-css-by-section)
11. [Icons & SVG specs](#11-icons--svg-specs)
12. [JavaScript module structure](#12-javascript-module-structure)
13. [Microcopy inventory](#13-microcopy-inventory)
14. [Responsive specs](#14-responsive-specs)
15. [Accessibility specs](#15-accessibility-specs)
16. [Browser support](#16-browser-support)
17. [Build & deployment](#17-build--deployment)

---

## 1. Quick-start: replicate in 5 steps

To stand this app up on another Windows machine:

1. **Copy the entire `Product Code Finder/` folder** to the target machine. All
   source, data, assets, and bundled Python are inside.
2. Ensure the target machine has internet access on first run (for Google
   Fonts). After first paint, fonts are browser-cached.
3. Double-click [run.bat](run.bat). It auto-detects the bundled Python in
   [python/](python/) or falls back to a system `py` launcher.
4. The browser opens to <http://127.0.0.1:5037> after ~14 seconds.
5. Done — no configuration, no installation steps.

To rebuild the UI **from scratch in a new project**, follow sections 2–17.

---

## 2. Full file inventory

### 2.1 Source files (must be copied verbatim)

| File | Size | Lines | Purpose |
|---|---:|---:|---|
| [app/templates/index.html](app/templates/index.html) | 12.5 KB | 275 | Single-page Jinja template |
| [app/static/styles.css](app/static/styles.css) | 40.2 KB | 1,561 | All styling, all tokens, all components |
| [app/static/app.js](app/static/app.js) | 33.3 KB | 894 | All client-side logic — vanilla JS, no framework |
| [app/static/avcon-logo.png](app/static/avcon-logo.png) | 45.3 KB | — | AVCON brand mark (see §4) |
| [app/server.py](app/server.py) | 6.8 KB | 197 | Flask routes, template rendering |
| [app/catalog.py](app/catalog.py) | 36.8 KB | 810 | Cascade-resolution catalog system |
| [app/accessories.py](app/accessories.py) | 6.4 KB | 180 | Flat-list accessories loader |

### 2.2 Data files (required for catalog to load)

| Path | Format | Approx size | Purpose |
|---|---|---:|---|
| `data/Valve/Ball Valve Data Set/Ball Valve Data Sheet Structure NEW OG - R01.xlsm` | XLSM | 1.4 MB | Ball valve master catalog |
| `data/Valve/Ball Valve Data Set/Valve_Code_Selector_Dashboard.xlsx` | XLSX | 3.2 MB | Ball valve actuator enrichment |
| `data/Valve/Butterfly Valve Data Set/Butterfly Valve Centric Data Sheet Structure OG - R01 (1).xlsm` | XLSM | 12.8 MB | Butterfly valve master catalog |
| `data/Valve/Butterfly Valve Data Set/4020B / 4022B / 4023B BFV NEW CODEING *.xlsx` | XLSX | ~2.5 MB each (3 files) | Butterfly per-series enrichment |
| `data/Actuator/Pneumatic Actuator/Rack & Pinion Data Sheet Structure new.xlsx` | XLSX | 0.6 MB | R&P actuator catalog |
| `data/Actuator/Pneumatic Actuator/Scotch Yoke Actuator Data Sheet Structure - 08.12.2025.xlsx` | XLSX | 0.3 MB | Scotch Yoke actuator catalog |
| `data/Actuator/Electrical Actuator/Electrical Actuator Rotory Data Sheet Structure - 09.12.2025.xlsx` | XLSX | 36 KB | Electrical rotary actuator catalog |
| `data/Accessories/Dashboard accessories.xlsx` | XLSX | 55 KB | Accessories dashboard (14 families) |

### 2.3 Distribution / launch files

| File | Purpose |
|---|---|
| [run.bat](run.bat) | Launch script — detects bundled Python or system `py` |
| [build_bundle.bat](build_bundle.bat) | Packages distribution ZIP for end users |
| [python/](python/) | Embedded Python 3.10+ runtime (~24 MB) — optional but used when bundling |

### 2.4 Documentation

| File | Audience |
|---|---|
| [README.txt](README.txt) | End users (sales team) — how to launch |
| [MAINTENANCE.txt](MAINTENANCE.txt) | Engineering — how to update catalog data |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Developers — code logic and architecture |
| **This file** ([DESIGN.md](DESIGN.md)) | Designers / UI replicators — complete frontend spec |

---

## 3. Dependencies & setup

### 3.1 Runtime

- **Python:** 3.10 or newer (3.14 used in development)
- **Browser:** any modern Chromium, Firefox, or Safari (uses CSS `:has()`, grid, custom properties — supported in all versions <2 years old)
- **OS:** Windows 10/11 primary target; macOS and Linux work via system Python

### 3.2 Python packages

```
flask>=2.0           # web framework
openpyxl>=3.1        # Excel reader (.xlsx + .xlsm)
```

That's it. No pandas, no SQLAlchemy, no JS build tools. Install via:

```bash
pip install flask openpyxl
```

OR use the bundled Python in [python/](python/) which already has them.

### 3.3 Network requirements

- **First run:** internet access to load Google Fonts (Roboto family)
- **Subsequent runs:** zero network — everything serves from `127.0.0.1`
- **Fonts:** browser caches them after first load; if you want offline-first,
  download the WOFF2 files and serve locally (see §5.3)

### 3.4 Port

App binds to `127.0.0.1:5037`. To change, edit `PORT = 5037` in
[app/server.py](app/server.py) line 25.

---

## 4. Logo asset specification

### 4.1 Source file

- **Path:** [app/static/avcon-logo.png](app/static/avcon-logo.png)
- **Format:** PNG, 8-bit RGBA (transparent background)
- **Native dimensions:** 374 × 166 pixels
- **Aspect ratio:** 2.253:1 (wider than tall)
- **File size:** 45,322 bytes (45.3 KB)
- **Color profile:** sRGB (standard)

### 4.2 Visual content (what's in the PNG)

- "AVCON" word-mark in teal `#017E80`, large
- "CONTROLS PVT. LTD." in smaller teal text below
- Italic tagline "Pioneer Spirit in Valve Automation" below that
- Registered trademark symbol `®` after "AVCON"
- All on transparent background

### 4.3 Usage in the app

| Property | Value |
|---|---|
| Rendered height | **52px** (CSS `height: 52px`) |
| Rendered width | auto (preserves aspect, ~117px wide at 52px tall) |
| Position | Top-right of header (pushed right via `margin-left: auto` in flex container) |
| Alt text | `AVCON Controls` |
| Padding around | 14px top/bottom, 40px right (inherits header padding) |

### 4.4 How to reproduce / replace

To swap the logo, replace `avcon-logo.png` with any PNG. The CSS sets a
fixed height (52px) and `width: auto`, so any aspect ratio works — the
image scales proportionally.

---

## 5. Font specification

### 5.1 Loaded font families

Three Google Fonts, loaded via one `<link>` in `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Slab:wght@400;600;700&family=Roboto+Mono:wght@400;500&display=swap">
```

### 5.2 Family details

| Family | Weights loaded | CSS variable | Used for |
|---|---|---|---|
| **Roboto** (sans-serif) | 300, 400, 500, 700 | `--c-font-sans` | Body text, labels, buttons, tags |
| **Roboto Slab** (serif) | 400, 600, 700 | `--c-font-serif` | Headings, page title, section titles, picker labels |
| **Roboto Mono** (monospace) | 400, 500 | `--c-font-mono` | Product codes, SKU identifiers |

### 5.3 System fallback stacks

If Google Fonts fails to load (offline / blocked), CSS falls back to:

```css
--c-font-sans:  "Roboto", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
--c-font-serif: "Roboto Slab", Georgia, "Times New Roman", serif;
--c-font-mono:  "Roboto Mono", "SF Mono", Consolas, monospace;
```

### 5.4 Offline-first option

To remove the Google Fonts dependency, download the WOFF2 files from
[fonts.google.com](https://fonts.google.com), place them in
`app/static/fonts/`, and add `@font-face` declarations at the top of
`styles.css`:

```css
@font-face {
  font-family: "Roboto";
  font-weight: 400;
  src: url("/static/fonts/Roboto-Regular.woff2") format("woff2");
  font-display: swap;
}
/* ...repeat for each weight × family combination... */
```

Then remove the `<link>` tags in `index.html`.

### 5.5 Base body type

```css
html, body {
  font-family: var(--c-font-sans);
  font-size: 15px;
  line-height: 1.55;
  font-weight: 400;
  color: #3a3a3a;
  background: #fcfcfc;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
```

---

## 6. Design tokens (`:root` CSS variables)

Every visual constant in the app comes from these. They're declared in
the top of [app/static/styles.css](app/static/styles.css) lines 8-53.
**Copy this entire block verbatim** when porting to another project:

```css
:root {
  /* Surfaces — clean industrial whites */
  --c-bg:         #fcfcfc;   /* page background — off-white */
  --c-surface:    #FFFFFF;   /* cards / panels */
  --c-surface-2:  #F5F5F5;   /* subtle alt surface, input bg on hover */
  --c-surface-3:  #EFEFEF;   /* code / nested surface */

  /* Borders — neutral gray */
  --c-border:        #E5E5E5;
  --c-border-strong: #D2D2D2;

  /* Text — near-black headings, slate body */
  --c-text:         #3a3a3a;
  --c-text-soft:    #4B4F58;
  --c-text-muted:   #7A7A7A;
  --c-text-subtle:  #9B9A93;

  /* Brand — AVCON teal */
  --c-accent:        #017E80;
  --c-accent-hover:  #016668;
  --c-accent-soft:   rgba(1, 126, 128, 0.10);
  --c-accent-ring:   rgba(1, 126, 128, 0.22);

  /* Secondary brand — AVCON corporate blue (used for sub-accents) */
  --c-accent-2:      #0170B9;

  /* Semantic — industrial-safe (not neon) */
  --c-warning:    #C97A00;
  --c-warning-bg: rgba(201, 122, 0, 0.10);
  --c-danger:     #B23A2E;

  /* Fonts — AVCON brand */
  --c-font-sans:  "Roboto", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --c-font-serif: "Roboto Slab", Georgia, "Times New Roman", serif;
  --c-font-mono:  "Roboto Mono", "SF Mono", Consolas, monospace;

  /* Shape & motion — squared-off, utilitarian */
  --c-radius-sm:  2px;
  --c-radius-md:  4px;
  --c-radius-lg:  6px;
  --c-radius-xl:  8px;
  --c-shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.04);
  --c-shadow-md:  0 1px 2px rgba(0, 0, 0, 0.04), 0 2px 8px rgba(0, 0, 0, 0.04);
  --c-shadow-lg:  0 2px 6px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.06);
  --c-transition: 180ms ease-out;
}
```

### 6.1 Color usage map (where each token shows up)

| Token | Hex / Value | Used in |
|---|---|---|
| `--c-bg` | `#fcfcfc` | `html, body` background; accessories list internal bg |
| `--c-surface` | `#FFFFFF` | All cards, picker boxes, dropdown menus, form inputs |
| `--c-surface-2` | `#F5F5F5` | Status box bg, hover state for inputs, alt-row stripes, code-card disabled |
| `--c-surface-3` | `#EFEFEF` | `<code>` blocks, code-card hover, disabled select bg |
| `--c-border` | `#E5E5E5` | Default card border, divider lines |
| `--c-border-strong` | `#D2D2D2` | Form input borders, picker box borders, button borders |
| `--c-text` | `#3a3a3a` | Headings, primary content text, form input text |
| `--c-text-soft` | `#4B4F58` | Form labels, table values, button text |
| `--c-text-muted` | `#7A7A7A` | Captions, tags, attribute lists, meta text |
| `--c-text-subtle` | `#9B9A93` | Placeholder text, "select —" options, footer |
| `--c-accent` | `#017E80` | Brand teal — title line 1, all buttons/chips/badges, focus rings, codes |
| `--c-accent-hover` | `#016668` | (Reserved — could be used for solid-button hover) |
| `--c-accent-soft` | `rgba(1, 126, 128, 0.10)` | Selected item bg, paired-actuator panel bg, chip pills |
| `--c-accent-ring` | `rgba(1, 126, 128, 0.22)` | 3px focus rings on inputs and dropdowns |
| `--c-accent-2` | `#0170B9` | (Reserved — corporate blue, not currently used) |
| `--c-warning` | `#C97A00` | Alt-match warning note text |
| `--c-warning-bg` | `rgba(201, 122, 0, 0.10)` | Alt-match warning note bg |
| `--c-danger` | `#B23A2E` | (Reserved — error state, not currently used) |
| `#B45309` (warm amber, not in `:root`) | `#B45309` | "Data Not Available" treatment, accessory placeholder headline |

### 6.2 Shape tokens

| Token | Value | Used for |
|---|---|---|
| `--c-radius-sm` | 2px | Small tags (section-subgroup), inline code |
| `--c-radius-md` | 4px | Form inputs, buttons, chips, code cards |
| `--c-radius-lg` | 6px | Picker boxes, workspace cards, accessories card |
| `--c-radius-xl` | 8px | (Reserved) |
| `999px` (literal) | full pill | Recommendation chips, summary chips, family tags, section subgroups |

### 6.3 Shadow tokens

| Token | Value | Used for |
|---|---|---|
| `--c-shadow-sm` | `0 1px 2px rgba(0,0,0,0.04)` | Picker boxes default, section cards |
| `--c-shadow-md` | `0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.04)` | Picker boxes hover, paired-card hover |
| `--c-shadow-lg` | `0 2px 6px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.06)` | Popover dropdown menus |

### 6.4 Motion

Single token: `--c-transition: 180ms ease-out`. Applied to all hover,
focus, color, and transform transitions. No staggered animations,
no complex easing.

### 6.5 Spacing scale (not tokenized, but consistent in use)

`2 · 4 · 6 · 8 · 10 · 12 · 14 · 16 · 18 · 20 · 22 · 24 · 28 · 32 · 40 · 60 · 480` (in pixels).
Increments of 2-4px at small scales, 4-8px at medium, 16-24px between cards.

---

## 7. Typography scale

Every text element in the UI with its exact properties:

| Element | CSS selector | Family | Size | Weight | Color | Other |
|---|---|---|---|---|---|---|
| **Page title line 1** (uppercase) | `.title-line:first-child` | serif | 26 × 0.78 = ~20.3px | 700 | `--c-accent` | uppercase, letter-spacing 0.02em |
| **Page title line 2** | `h1` inside header | serif | 26px | 700 | `--c-text` | letter-spacing -0.005em, line-height 1.18 |
| **Tagline** | `.tagline` | sans | 13px | 400 italic | `--c-text-muted` | — |
| **Top picker prefix** | `.type-picker-trigger-prefix` | sans | 11.5px | 500 | `--c-text-muted` | uppercase, letter-spacing 0.06em, padding-right 12px, border-right 1px |
| **Top picker label** | `.type-picker-trigger-label` | serif | 16px | 500 | `--c-text` (→ accent when selected) | flex:1 |
| **Picker menu subheader** | `.type-picker-subheader` | sans | 10.5px | 600 | `--c-text-muted` | uppercase, letter-spacing 0.08em |
| **Picker menu option title** | `.option-title` | serif | 15px | 500 | `--c-text` (→ accent when active) | letter-spacing -0.005em |
| **Picker menu option meta** | `.option-meta` | sans | 11.5px | 400 | `--c-text-muted` | truncates at 280px |
| **Workspace card header** | `.workspace-col-header` | serif | 18px | 500 | `--c-text` | with 6px teal bar prefix + 22px icon circle |
| **Empty page prompt** | `.empty-prompt` | sans | 14px | 400 italic | `--c-text-muted` | center |
| **Column placeholder hint** | `.column-placeholder` | sans | 13px | 400 | `--c-text-muted` | center, padding 28px 12px |
| **Section title (inside card)** | `.section-head .section-title` | serif | 22px (18px inside workspace-col) | 500 | `--c-text` | letter-spacing -0.01em |
| **Section subgroup tag** | `.section-subgroup` | sans | 10.5px | 600 | `--c-accent` | uppercase, pill shape, teal-soft bg |
| **Section meta (SKU count)** | `.section-meta` | sans | 12.5px | 400 | `--c-text-muted` | — |
| **Section h2 (Selection / Your Match)** | `section h2` | sans | 13px | 600 | `--c-text-muted` | letter-spacing 0.02em |
| **Form field label** | `.row label` | sans | 13px | 500 | `--c-text-soft` | margin-bottom 6px |
| **Form select / input** | `.row select, .row input[list]` | sans | 14px | 400 | `--c-text` | padding 10px 14px |
| **Reset button** | `.actions button` | sans | 13.5px | 500 | `--c-text-soft` | padding 9px 18px |
| **Status line** | `.status` | sans | 14px | 400 | `--c-text-muted` | padding 14px 16px, surface-2 bg |
| **Code card label** | `.code-label` | sans | 12px | 500 | `--c-text-muted` | margin-bottom 6px |
| **Code card value** | `.code-value` | mono | 15px | 500 | `--c-text` | word-break: break-all |
| **Alt-match warning** | `.alt-note` | sans | 13px | 400 | `--c-warning` | padding 12px 14px |
| **Details summary** | `details summary` | sans | 13.5px | 500 | `--c-text-soft` | with CSS chevron marker |
| **Details table key** | `table th` | sans | 13px | 500 | `--c-text-muted` | width 240px, surface-2 bg |
| **Details table value** | `table td` | mono | 13px | 400 | `--c-text` | word-break: break-word |
| **Paired section header** | `.paired-section-header` | sans | 11.5px | 700 | `--c-accent` | uppercase, letter-spacing 0.08em |
| **Paired option num** | `.paired-option-num` | sans | 12.5px | 600 | `--c-text` | — |
| **Paired option category** | `.paired-option-cat` | sans | 12.5px | 500 | `--c-accent` | with `—` separator before |
| **Recommendation chip code** | `.paired-chip-code` | mono | 13px | 600 | `--c-accent` (→ surface on hover) | nowrap, letter-spacing -0.005em |
| **Recommendation chip label** | `.paired-chip-label` | sans | 11px | 400 | `--c-text-muted` (→ surface on hover) | line-height 1.3, wraps |
| **Accessories card title** | `.accessories-title` | serif | 18px | 500 | `--c-text` | with 6px teal bar prefix + 22px icon |
| **Accessories count meta** | `.accessories-count` | sans | 12px | 400 | `--c-text-muted` | right-aligned |
| **Accessories picker prefix** | `.accessories-filter-label` | sans | 11.5px | 500 | `--c-text-muted` | uppercase, letter-spacing 0.06em, border-right 1px |
| **Accessories picker label** | `.accessories-filter select` | serif | 16px | 500 | `--c-accent` | — |
| **Accessories search label** | `.accessories-search-label` | sans | 10.5px | 600 | `--c-text-muted` | uppercase, letter-spacing 0.04em |
| **Accessories search input** | `.accessories-search input` | sans | 13px | 400 | `--c-text` | padding 7px 10px |
| **Accessories selected count** | `.selected-count` | sans | 12.5px | 500 | `--c-text-soft` | — |
| **Accessories clear button** | `.accessories-clear-btn` | sans | 12px | 400 | `--c-text-soft` | padding 6px 12px |
| **Accessories family-group name** | `.acc-group-name` | serif | 13px | 600 | `--c-text` | sticky header |
| **Accessories family-group count** | `.acc-group-count` | sans | 11px | 500 | `--c-text-muted` | — |
| **Accessories item code** | `.acc-item-code` | mono | 13.5px | 600 | `--c-accent` | — |
| **Accessories item attrs** | `.acc-item-attrs` | sans | 12px | 400 | `--c-text-muted` | line-height 1.4 |
| **Summary panel title** | `.summary-title` | serif | 16px | 600 | `--c-accent` | uppercase, with `★` prefix |
| **Summary card label** | `.summary-label` | sans | 11px | 700 | `--c-text-muted` | uppercase, letter-spacing 0.08em |
| **Summary card code** | `.summary-code` | mono | 22px | 600 | `--c-accent` | letter-spacing -0.005em |
| **Summary card name** | `.summary-name` | sans | 13px | 400 | `--c-text-soft` | line-height 1.35 |
| **Summary acc chip family** | `.summary-acc-chip-family` | sans | 9.5px | 700 | `--c-surface` (white) on solid teal | uppercase, letter-spacing 0.05em |
| **Summary acc chip code** | `.summary-acc-chip-code` | mono | 11.5px | 500 | `--c-accent` | — |
| **Footer** | `footer` / `footer small` | sans | 12.5px | 400 | `--c-text-subtle` | center |

---

## 8. Layout structure

### 8.1 Page-level skeleton

```
<body>
  <header>            ← AVCON brand strip
  <div.picker-row>    ← Top dropdowns (Valves, Actuators)
  <p.empty-prompt>    ← "Pick a type from the menus above to start"
  <div.workspace>     ← The main grid (5 areas)
    <div.workspace-col workspace-col--valves>
    <div.workspace-col workspace-col--actuators>
    <div.workspace-accessories>
    <div.workspace-summary>
  </div>
  <footer>            ← "Local-only tool · no data leaves this machine"
</body>
```

### 8.2 Workspace grid

```css
.workspace {
  max-width: 1400px;
  margin: 0 auto 32px;
  padding: 0 24px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-areas:
    "valves     actuators"
    "access     access"
    "summary    summary";
  gap: 24px;
  align-items: start;
}
.workspace-col--valves     { grid-area: valves; }
.workspace-col--actuators  { grid-area: actuators; }
.workspace-summary         { grid-area: summary; }
.workspace-accessories     { grid-area: access; }
```

### 8.3 Container max-widths

| Container | max-width | Notes |
|---|---|---|
| Header | 1280px | centered with `margin: 0 auto` |
| Picker row | 1280px | centered |
| Empty prompt | 1280px | centered |
| **Workspace grid** | **1400px** | slightly wider than header for breathing room |
| Footer | 1280px | centered |
| Section-head (legacy) | 1280px | inside `.valve-section`, overridden inside workspace-col |
| Workspace-col cards | (fills grid cell, no max) | half the workspace width on desktop |
| Accessories list inside | 100% of card | with `max-height: 480px` and scroll |
| Type-picker menu | min-width 360px | popover |
| Accessory placeholder sub-text | 620px | centered within card |

### 8.4 Horizontal padding by section

| Section | Padding |
|---|---|
| `header` | `14px 40px` |
| `.picker-row` | `0 40px` |
| `.workspace` | `0 24px` |
| `.workspace-col` | `18px 22px` |
| `.workspace-accessories` | `18px 22px` |
| `.workspace-summary` | `18px 22px` |
| `footer` | `14px 24px 18px` |

---

## 9. Complete HTML template

This is [app/templates/index.html](app/templates/index.html) verbatim.
Jinja directives (`{{ }}` and `{% %}`) need a backend that provides
`sections`, `category_blocks`, `total_skus`, `accessories_summary` — see
section 12.6 for the data shapes.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Valve & Actuator Code Selector</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Slab:wght@400;600;700&family=Roboto+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}" />
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-text">
        <h1>
          <span class="title-line">BV&ndash;BFV&ndash;Actuator&ndash;Accessory</span>
          <span class="title-line">Product Code Finder</span>
        </h1>
        <p class="tagline">{{ "{:,}".format(total_skus) }} AVCON SKUs. Infinite Specs. One Click.</p>
      </div>
      <img src="{{ url_for('static', filename='avcon-logo.png') }}" alt="AVCON Controls" class="brand-logo" />
    </div>
  </header>

  <!-- One picker widget per category. Independent selections. -->
  <div class="picker-row">
    {% for cat in category_blocks %}
    <nav class="type-picker" data-category="{{ cat.name }}">
      <button type="button" class="type-picker-trigger"
              aria-haspopup="true" aria-expanded="false">
        <span class="type-picker-trigger-prefix">{{ cat.name }}</span>
        <span class="type-picker-trigger-label">Choose {{ cat.name|lower|trim('s') }} type</span>
        <svg class="type-picker-chevron" viewBox="0 0 12 8" aria-hidden="true">
          <path d="M1 1.5l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <div class="type-picker-menu" role="menu" hidden>
        {% for sg in cat.subgroups %}
        {% if sg.name %}
        <div class="type-picker-subheader">{{ sg.name }}</div>
        {% endif %}
        {% for item in sg.members %}
        <button type="button" class="type-picker-option" role="menuitem" data-valve-type="{{ item.key }}">
          <span class="option-icon" aria-hidden="true">
            <!-- Per-type SVG icons — see §11 -->
          </span>
          <span class="option-text">
            <span class="option-title">{{ item.label }}</span>
            <span class="option-meta">{{ "{:,}".format(item.row_count) }} SKUs</span>
          </span>
        </button>
        {% endfor %}
        {% endfor %}
      </div>
    </nav>
    {% endfor %}
  </div>

  <p class="empty-prompt" id="empty-prompt">Pick a type from the menus above to start.</p>

  <div class="workspace">

    {% macro render_section(section) %}
    <article class="valve-section" data-valve-type="{{ section.key }}" data-category="{{ section.category }}" hidden>
      <div class="section-head">
        <h2 class="section-title">
          {% if section.subgroup %}<span class="section-subgroup">{{ section.subgroup }}</span>{% endif %}
          {{ section.label }}
        </h2>
        <p class="section-meta">
          {{ "{:,}".format(section.row_count) }} {{ section.category|lower|trim('s') }} SKUs
        </p>
      </div>

      <main>
        <section class="form-panel">
          <h2>Selection</h2>
          <form class="picker" autocomplete="off">
            {% for field in section.cascade %}
            <div class="row" data-field="{{ field.key }}">
              <label for="f-{{ section.key }}-{{ field.key }}">{{ field.label }}</label>
              {% if field.key in ("series", "model") %}
              <input id="f-{{ section.key }}-{{ field.key }}" name="{{ field.key }}" data-key="{{ field.key }}"
                     list="{{ section.key }}-{{ field.key }}-options" autocomplete="off" spellcheck="false"
                     placeholder="Type to search…" />
              <datalist id="{{ section.key }}-{{ field.key }}-options"></datalist>
              {% else %}
              <select id="f-{{ section.key }}-{{ field.key }}" name="{{ field.key }}" data-key="{{ field.key }}">
                <option value="">— select —</option>
              </select>
              {% endif %}
            </div>
            {% endfor %}
            <div class="row actions">
              <button type="button" class="reset-btn">Reset</button>
            </div>
          </form>
        </section>

        <section class="result-panel">
          <h2>Your Match</h2>
          <div class="status">Pick {{ section.cascade[0].label }} to begin.</div>

          <div class="codes" hidden>
            <div class="code-card">
              <div class="code-label">{{ section.primary_label }}</div>
              <div class="code-value primary-code">—</div>
            </div>
            {% if section.secondary_label %}
            <div class="code-card">
              <div class="code-label">{{ section.secondary_label }}</div>
              <div class="code-value secondary-code">—</div>
            </div>
            {% endif %}
            {% if section.show_bto_fos %}
            <div class="code-card">
              <div class="code-label">BTO (N·m)</div>
              <div class="code-value bto">—</div>
            </div>
            <div class="code-card">
              <div class="code-label">FOS = BTO × 1.5</div>
              <div class="code-value fos">—</div>
            </div>
            {% endif %}
          </div>

          <div class="alt-note" hidden></div>
          <div class="paired-actuator" hidden></div>

          <details class="details-wrap" hidden>
            <summary>All attributes</summary>
            <table class="details">
              <tbody></tbody>
            </table>
          </details>
        </section>
      </main>
    </article>
    {% endmacro %}

    <div class="workspace-col workspace-col--valves">
      <h2 class="workspace-col-header">
        <span class="workspace-col-icon" aria-hidden="true">◐</span>
        Valves
      </h2>
      <p class="column-placeholder">
        Pick a <strong>valve type</strong> from the menu above.
      </p>
      {% for section in sections if section.category == 'Valves' %}
        {{ render_section(section) }}
      {% endfor %}
    </div>

    <div class="workspace-col workspace-col--actuators">
      <h2 class="workspace-col-header">
        <span class="workspace-col-icon" aria-hidden="true">◑</span>
        Actuators
      </h2>
      <p class="column-placeholder">
        Pick an <strong>actuator type</strong>, or use a valve's recommendation.
      </p>
      {% for section in sections if section.category == 'Actuators' %}
        {{ render_section(section) }}
      {% endfor %}
    </div>

    <div class="workspace-accessories" id="workspace-accessories">
      <h2 class="accessories-title">
        <span class="accessories-icon" aria-hidden="true">+</span>
        Accessories
        {% if accessories_summary.row_count %}
        <span class="accessories-count">{{ accessories_summary.row_count }} items · {{ accessories_summary.family_count }} families</span>
        {% endif %}
      </h2>

      {% if not accessories_summary.row_count %}
      <div class="accessories-placeholder">
        <p class="accessories-placeholder-headline">Data pending</p>
        <p class="accessories-placeholder-sub">
          Please provide the accessories catalog file at
          <code>data/Accessories/Dashboard accessories.xlsx</code>.
        </p>
      </div>
      {% else %}
      <div class="accessories-toolbar">
        <label class="accessories-filter">
          <span class="accessories-filter-label">ACCESSORIES</span>
          <select id="accessories-family-filter">
            <option value="">All families</option>
          </select>
        </label>
        <label class="accessories-search">
          <span class="accessories-search-label">Search</span>
          <input type="search" id="accessories-search-input"
                 placeholder="Filter by code or attribute…" autocomplete="off" />
        </label>
        <div class="accessories-selected-summary" id="accessories-selected-summary">
          <span class="selected-count" id="accessories-selected-count">0 selected</span>
          <button type="button" class="accessories-clear-btn" id="accessories-clear-btn" hidden>
            Clear all
          </button>
        </div>
      </div>

      <div class="accessories-list" id="accessories-list" role="list">
        <div class="accessories-loading">Loading accessories…</div>
      </div>
      {% endif %}
    </div>

    <div class="workspace-summary" id="workspace-summary" hidden>
      <h2 class="summary-title">Your Product Code is</h2>
      <div class="summary-grid">
        <div class="summary-card summary-card--valve" data-summary-category="Valves" hidden>
          <div class="summary-label">Valve</div>
          <div class="summary-code">—</div>
          <div class="summary-name">—</div>
        </div>
        <div class="summary-card summary-card--actuator" data-summary-category="Actuators" hidden>
          <div class="summary-label">Actuator</div>
          <div class="summary-code">—</div>
          <div class="summary-name">—</div>
        </div>
      </div>
      <div class="summary-card summary-card--accessories" id="summary-accessories" hidden>
        <div class="summary-label">Accessories (<span class="summary-acc-count">0</span>)</div>
        <div class="summary-acc-list">—</div>
      </div>
    </div>

  </div>

  <footer>
    <small>Local-only tool · no data leaves this machine</small>
  </footer>

  <script src="{{ url_for('static', filename='app.js') }}"></script>
</body>
</html>
```

---

## 10. Complete CSS by section

The full CSS is 1,561 lines. Rather than embed all of it inline (it's
better to copy the file directly), this section catalogs **what's in each
block** so you know where to look in [app/static/styles.css](app/static/styles.css).

### 10.1 Source-file outline

| Lines | Section | Notes |
|---|---|---|
| 1-6 | File header comment | Brand theme attribution |
| 8-53 | `:root` CSS variables | All design tokens (see §6) |
| 55-76 | Global resets | `box-sizing`, `[hidden]`, body, `::selection` |
| 78-149 | Header / brand | Logo (52px height, right-aligned via `margin-left:auto`), title block |
| 151-160 | `main` grid (legacy) | 360px + 1fr — overridden by workspace-col when nested |
| 162-178 | Generic `section` styles | Card chrome — white bg, 1px border, 6px radius, padding 24px 26px |
| 180-222 | Form rows (`.row`, `.row select`) | Label + select with custom chevron SVG, hover/focus/disabled states |
| 224-252 | Action buttons (Reset) | Padding 9px 18px, gray border, hover bg shift |
| 254-264 | `.status` line | Surface-2 bg with border, padding 14px 16px |
| 266-299 | `.codes` grid + `.code-card` | 2-col grid, 12px gap; cards have label + mono value |
| 301-311 | `.alt-note` (warning) | Amber warning style for multi-match |
| 313-355 | `details summary` disclosure | Custom CSS chevron rotation on open |
| 356-393 | `table.details` | Detail attributes table; 240px key column, mono values |
| 395-406 | `footer` | Centered, subtle text, top border |
| 408-416 | Responsive (`<860px`) | Stack main grid, narrow padding |
| 418-452 | Typeahead `.row input[list]` | Mirror of select styling with search-icon SVG |
| 454-513 | `.valve-section` (legacy) | Used outside workspace; overridden when inside workspace-col |
| 515-523 | `.picker-row` | Top picker container, flex with 16px gap, max 1280px |
| 525-560 | `.type-picker-trigger` | The white dropdown box (320-360px wide, padding 14px 22px) |
| 562-582 | `.type-picker-trigger-prefix` + label | Prefix has vertical right-border separator |
| 584-593 | `.type-picker-chevron` | Rotates 180deg when open |
| 595-634 | `.type-picker-menu` popover | Position absolute, animated entry (`menu-pop` keyframe) |
| 636-708 | `.type-picker-option` | Menu items with 40×40 icon box + title + meta |
| 710-727 | `.empty-prompt` + mobile picker-row | Italic muted text, mobile stacks |
| 729-814 | `.paired-card` (legacy) | Older recommendation-card style, kept defensively |
| 816-850 | `.paired-card--unavailable` | "Data Not Available" amber treatment for cards |
| 852-982 | `.paired-section` + chips (CURRENT) | The chip-grouped recommendation panel |
| 984-999 | `.section-subgroup` tag | Pill-shaped category badge in section titles |
| 1001-1097 | Workspace grid + columns + placeholder | The main `.workspace` 4-area grid; column cards |
| 1099-1129 | Workspace nested overrides | Inside workspace-col, sections lose padding/max-width |
| 1131-1189 | `.workspace-summary` | Center band with gradient teal-soft → white |
| 1192-1262 | `.workspace-accessories` + placeholder | Accessories card with optional "Data pending" empty state |
| 1264-1395 | Accessories browse UI | Toolbar (picker box + search + selected count + clear) |
| 1397-1492 | Accessories list | Scrollable, family-grouped, sticky headers, checkbox rows |
| 1494-1532 | `.summary-card--accessories` chips | Family tag (solid teal) + code (mono teal) |
| 1534-1561 | Responsive (`<980px`) | Workspace grid → single column; toolbar wraps |

### 10.2 Key component CSS (for fastest reference)

The 8 most-used components, with their complete CSS embedded:

#### Picker box (the white dropdown shape used in 3 places)

```css
.type-picker-trigger {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  padding: 14px 22px;
  background: var(--c-surface);
  border: 1px solid var(--c-border-strong);
  border-radius: var(--c-radius-lg);
  cursor: pointer;
  font-family: var(--c-font-sans);
  font-size: 14px;
  color: var(--c-text);
  box-shadow: var(--c-shadow-sm);
  transition: all var(--c-transition);
  min-width: 320px;
}
.type-picker-trigger:hover {
  background: var(--c-surface-2);
  border-color: var(--c-text-subtle);
  box-shadow: var(--c-shadow-md);
}
.type-picker-trigger:focus-visible {
  outline: none;
  border-color: var(--c-accent);
  box-shadow: 0 0 0 3px var(--c-accent-ring);
}
.type-picker-trigger-prefix {
  font-size: 11.5px;
  font-weight: 500;
  color: var(--c-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding-right: 12px;
  border-right: 1px solid var(--c-border);
}
.type-picker-trigger-label {
  flex: 1;
  font-family: var(--c-font-serif);
  font-size: 16px;
  font-weight: 500;
  color: var(--c-text);
  text-align: left;
}
.type-picker-chevron {
  width: 12px;
  height: 8px;
  color: var(--c-text-muted);
  transition: transform var(--c-transition), color var(--c-transition);
}
.type-picker.open .type-picker-chevron {
  transform: rotate(180deg);
  color: var(--c-accent);
}
```

#### Workspace column card (Valves / Actuators)

```css
.workspace-col {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--c-radius-lg);
  padding: 18px 22px;
  min-height: 160px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.workspace-col-header {
  margin: 0 0 4px;
  font-family: var(--c-font-serif);
  font-size: 18px;
  font-weight: 500;
  color: var(--c-text);
  display: flex;
  align-items: center;
  gap: 10px;
}
.workspace-col-header::before {
  content: "";
  display: inline-block;
  width: 6px;
  height: 18px;
  background: var(--c-accent);
  border-radius: 2px;
}
.workspace-col-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--c-accent-soft);
  color: var(--c-accent);
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
}
```

#### Recommendation chip (model + position label)

```css
.paired-chip {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 7px 14px;
  background: var(--c-surface);
  border: 1px solid var(--c-accent);
  border-radius: var(--c-radius-md);
  cursor: pointer;
  transition: all var(--c-transition);
  text-align: left;
  max-width: 240px;
  min-width: 0;
}
.paired-chip-code {
  font-family: var(--c-font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--c-accent);
  white-space: nowrap;
  letter-spacing: -0.005em;
}
.paired-chip-label {
  font-family: var(--c-font-sans);
  font-size: 11px;
  font-weight: 400;
  color: var(--c-text-muted);
  line-height: 1.3;
}
.paired-chip:hover {
  background: var(--c-accent);
  border-color: var(--c-accent);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(1, 126, 128, 0.25);
}
.paired-chip:hover .paired-chip-code,
.paired-chip:hover .paired-chip-label {
  color: var(--c-surface);
}
.paired-chip--unavailable {
  background: var(--c-surface-2);
  border-color: var(--c-border-strong);
  cursor: not-allowed;
}
.paired-chip--unavailable .paired-chip-code {
  color: #B45309;
  font-style: italic;
}
```

#### Summary card (Valve / Actuator)

```css
.summary-card {
  background: var(--c-surface);
  border: 1px solid var(--c-accent);
  border-radius: var(--c-radius-md);
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.summary-label {
  font-family: var(--c-font-sans);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-text-muted);
}
.summary-code {
  font-family: var(--c-font-mono);
  font-size: 22px;
  font-weight: 600;
  color: var(--c-accent);
  letter-spacing: -0.005em;
}
.summary-name {
  font-family: var(--c-font-sans);
  font-size: 13px;
  color: var(--c-text-soft);
  line-height: 1.35;
}
```

#### Summary accessory chip (family + code)

```css
.summary-acc-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px 3px 4px;
  background: var(--c-accent-soft);
  border: 1px solid var(--c-accent);
  border-radius: 999px;
  white-space: nowrap;
}
.summary-acc-chip-family {
  display: inline-block;
  padding: 2px 7px;
  font-family: var(--c-font-sans);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--c-surface);
  background: var(--c-accent);
  border-radius: 999px;
  line-height: 1.2;
}
.summary-acc-chip-code {
  font-family: var(--c-font-mono);
  font-size: 11.5px;
  font-weight: 500;
  color: var(--c-accent);
}
```

### 10.3 Critical CSS to copy verbatim

If you only have time to copy 6 things, copy these blocks from
[app/static/styles.css](app/static/styles.css):

1. **Lines 8-53** — the `:root` token block
2. **Lines 78-149** — header + brand layout
3. **Lines 515-708** — top picker boxes + popover menus
4. **Lines 852-982** — recommendation chip section
5. **Lines 1001-1262** — workspace grid + accessories card
6. **Lines 1494-1561** — summary chips + responsive

That gives you ~600 lines covering the entire user-visible UI. The rest
(form rows, code cards, tables, details, alt-note) is generic chrome
that's safe to omit if you don't need those subcomponents.

---

## 11. Icons & SVG specs

### 11.1 Per-product-type icons (in picker menu options)

Embedded inline in [index.html](app/templates/index.html) lines 47-58.
All use `viewBox="0 0 24 24"`, `stroke="currentColor"`, `stroke-width="1.6"`.

| Product | SVG path |
|---|---|
| Ball valve | `<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5" fill="currentColor"/>` |
| Butterfly valve | `<circle cx="12" cy="12" r="8"/><ellipse cx="12" cy="12" rx="7.5" ry="1.5"/><line x1="4" y1="12" x2="20" y2="12"/>` |
| Pneumatic R&P | `<rect x="4" y="9" width="16" height="6" rx="1"/><circle cx="12" cy="12" r="2.5"/>` |
| Pneumatic Scotch Yoke | `<rect x="5" y="8" width="10" height="8" rx="1"/><line x1="15" y1="12" x2="20" y2="12"/><circle cx="20" cy="12" r="1.5"/>` |
| Electrical Rotary | `<path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" fill="currentColor" stroke="none"/>` (lightning bolt) |
| Fallback | `<circle cx="12" cy="12" r="7"/>` |

Rendered inside a 40×40 `.option-icon` box with 22px SVG sizing.

### 11.2 Type-picker chevron

```html
<svg class="type-picker-chevron" viewBox="0 0 12 8" aria-hidden="true">
  <path d="M1 1.5l5 5 5-5"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"/>
</svg>
```

Size: 12 × 8 px. Color inherits from text (muted gray → teal when open).

### 11.3 Form select chevron (different — slightly smaller stroke)

Embedded as data-URI background image in `.row select`:
```css
background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path fill='none' stroke='%2371706B' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round' d='M1 1.5l5 5 5-5'/></svg>");
```
Stroke color is hardcoded `#71706B` (URL-encoded `%23`).

### 11.4 Search icon (typeahead inputs for Series, Model)

```css
background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 16 16'><circle cx='7' cy='7' r='5' fill='none' stroke='%2371706B' stroke-width='1.5'/><path d='M14 14l-3-3' stroke='%2371706B' stroke-width='1.5' stroke-linecap='round'/></svg>");
```

### 11.5 Unicode glyphs used as icons

| Glyph | Codepoint | Where used | Why |
|---|---|---|---|
| `◐` | U+25D0 | Valves workspace-col-icon | Half-moon — visual ID for Valves |
| `◑` | U+25D1 | Actuators workspace-col-icon | Other half-moon — pair to Valves |
| `+` | U+002B | Accessories title icon | Plus sign — add/append meaning |
| `★` | U+2605 | Summary title prefix | Marks the "final result" panel |
| `–` (en-dash) | U+2013 | Title separator (`BV–BFV–ACTUATOR–ACCESSORY`) | Brand styling |
| `—` (em-dash) | U+2014 | Picker option separator (`Option 1 — Pneumatic`), select placeholder (`— select —`) | Reading rhythm |
| `▾` (chevron, as SVG) | n/a | All dropdown triggers | Custom SVG, see §11.2-11.4 |
| `·` (interpunct) | U+00B7 | Joining attribute values ("ALR · Aluminum · 1/4\" BSP"), tagline separator | Less visual weight than comma |

### 11.6 Details disclosure marker (CSS-only chevron)

```css
details summary::before {
  content: "";
  display: inline-block;
  width: 8px; height: 8px;
  border-right: 1.5px solid var(--c-text-muted);
  border-bottom: 1.5px solid var(--c-text-muted);
  transform: rotate(-45deg) translate(2px, -2px);
  transition: transform var(--c-transition);
}
details[open] summary::before {
  transform: rotate(45deg) translate(0px, -2px);
}
```

Two right-angle borders rotated to form an arrow. Pure CSS, no SVG needed.

---

## 12. JavaScript module structure

[app/static/app.js](app/static/app.js) is 894 lines of vanilla JS — no
framework, no build step. The file defines 5 classes + 1 module function
all at the same scope:

### 12.1 `Picker` class (5 instances at runtime)

One per `<article class="valve-section">`. Wires up:
- The cascade form (selects + typeahead inputs)
- `/api/<type>/options` requests on field change (refresh downstream options)
- `/api/<type>/resolve` request when cascade is complete
- Result-panel rendering (codes + recommendation chips + details table)
- Emits `valve-selector:resolved` and `valve-selector:cleared` events

```
constructor(sectionEl)
  → reads field elements, binds change handlers
init()
  → first paint
refreshOptions() / refreshResolution() / refreshAll()
setFieldValue(key, value) — used by recommendation chips
_renderResult(d) — populates code cards + status + paired-actuator + details
_renderPairedActuators(list) — builds the chip section
_renderPairedChip(paired) — one chip
_emitResolvedEvent(d) / _emitClearedEvent() — to SummaryPanel
```

### 12.2 `TypePicker` class (2 instances)

One per `<nav class="type-picker">`. Handles the top dropdown UX:
- Click trigger → open/close popover menu
- Click option → set as active, show that section, close menu
- Click already-active option → deselect (back to empty state)
- ESC / outside click → close

### 12.3 `viewMatchingActuator(targetType, targetField, value)` function

Module-level. Triggered when a recommendation chip is clicked:
1. Calls `TypePicker.select()` to open the target actuator family
2. Calls `Picker.setFieldValue("model", value)` to pre-fill
3. Scrolls the actuator section into view

### 12.4 `SummaryPanel` class (1 instance)

Listens for `valve-selector:resolved` / `valve-selector:cleared`. Updates
the Valve and Actuator cards in the bottom summary panel based on which
catalog resolved. Tracks `activeKeyByCategory` so a `cleared` event from a
previously-selected catalog doesn't accidentally wipe the new one.

### 12.5 `AccessoryBrowser` class (1 instance)

Manages the accessories card:
- Fetches `/api/accessories/list` on load
- Renders rows grouped by family with checkboxes
- Family filter dropdown + free-text search (both client-side)
- **One-per-family selection constraint** via `_deselectSameFamily()`
- Broadcasts `accessories:selected-changed` with the current selection

### 12.6 `AccessorySummary` class (1 instance)

Listens for `accessories:selected-changed`. Renders selected accessories
as family-tag + code chips in the summary panel.

### 12.7 Data shapes (what backend provides to template)

```python
# Each `section` (passed as list to template):
{
    "key": "ball",                          # URL identifier
    "label": "Ball Valve",                  # display name
    "category": "Valves",                   # "Valves" or "Actuators"
    "subgroup": None | "Pneumatic" | "Electrical",
    "source_file": "Ball Valve…xlsm",       # (now hidden from UI)
    "row_count": 3892,
    "cascade": [{"key": "series", "label": "Series"}, ...],
    "primary_label": "Bare Valve Code",
    "secondary_label": "Catalogue Code",
    "show_bto_fos": True,
}

# `category_blocks` (for top picker row):
[{
    "name": "Valves",
    "subgroups": [{"name": "", "members": [section, section]}],
}, ...]

# `accessories_summary`:
{"row_count": 162, "family_count": 13, "source_file": "Dashboard...xlsx"}

# `total_skus`: 49289 (sum across all sections)
```

### 12.8 API endpoints the JS calls

```
GET /api/<valve_type>/options?picks={JSON}
    → {field_key: [option1, option2, ...], ...}

GET /api/<valve_type>/resolve?picks={JSON}
    → {"matched": true, "detail": {primary, secondary, bto, fos,
                                    paired_actuators: [...], fields: [...],
                                    match_count}}
    OR {"matched": false}

GET /api/accessories/list
    → {"rows": [{code, family, attrs: [{label, value}]}], "families": [...]}

GET /api/health
    → {"ok": true, "types": {key: {rows, category, subgroup, source}}}
```

### 12.9 Custom events

| Event | Detail | Emitted by | Listened by |
|---|---|---|---|
| `valve-selector:resolved` | `{key, category, sectionLabel, primary, secondary, actuatorName, actuatorType}` | `Picker._emitResolvedEvent` | `SummaryPanel` |
| `valve-selector:cleared` | `{key, category}` | `Picker._emitClearedEvent` | `SummaryPanel` |
| `accessories:selected-changed` | `{rows: [...]}` | `AccessoryBrowser._broadcast` | `AccessorySummary` |

All events bubble to `document`. No EventEmitter / RxJS / etc. — just
native `CustomEvent` + `addEventListener`.

---

## 13. Microcopy inventory

Every visible string in the UI. Strings in `{braces}` are dynamic.

### Header
- Title line 1: `BV–BFV–Actuator–Accessory` (CSS uppercases on render)
- Title line 2: `Product Code Finder`
- Tagline: `{total_skus} AVCON SKUs. Infinite Specs. One Click.`
- Logo alt text: `AVCON Controls`

### Top picker dropdowns
- Prefix: `VALVES`, `ACTUATORS` (category name uppercased via CSS `text-transform`)
- Default label: `Choose {category|singular} type` (e.g., `Choose valve type`)
- Subgroup headers inside menu: `Pneumatic`, `Electrical`
- Option labels (dynamic): `Ball Valve`, `Butterfly Valve (Centric)`, `Rack & Pinion`, `Scotch Yoke`, `Rotary`
- Option meta: `{N,N} SKUs`

### Empty / waiting states
- Page-level: `Pick a type from the menus above to start.`
- Valves placeholder: `Pick a valve type from the menu above.`
- Actuators placeholder: `Pick an actuator type, or use a valve's recommendation.`

### Section card headers
- Workspace col header (Valves card): `Valves`
- Workspace col header (Actuators card): `Actuators`
- Accessories card title: `Accessories` + `{N} items · {M} families` (dynamic count)
- Summary panel title: `Your Product Code is` (CSS uppercases)

### Cascade form
- Selection panel heading: `Selection`
- Field labels (dynamic per cascade): `Series`, `Valve Size`, `Body Material`, etc.
- Select placeholder option: `— select —`
- Typeahead input placeholder: `Type to search…`
- Reset button: `Reset`

### Result panel
- Heading: `Your Match`
- Initial status: `Pick {first field} to begin.`
- In-progress status: `Continue selecting ({N}/{M}).`
- Resolved status: `Here's your match!`
- No-match status: `No SKU matches this combination.`
- Multi-match status: `{N} catalog rows matched these picks — showing the first.`
- Code card labels: `Bare Valve Code`, `Catalogue Code`, `BTO (N·m)`, `FOS = BTO × 1.5`, `Code`, `Model`
- Disclosure summary: `All attributes`

### Recommendation panel
- Section heading: `RECOMMENDED ACTUATOR` (visually uppercase via CSS)
- Group label format: `Option {N} — {Pneumatic|Electric}`
- Chip code = source data value (e.g., `ACT-050D`)
- Chip label = position description (e.g., `Double Acting @ 3.5 bar`, `Spring Return Fail-Close @ 5.5 bar`)
- Tooltip on chip: `{label} · {actuator friendly name}` (e.g., `Spring Return Fail-Close · Pneumatic Rack & Pinion Actuator — Single Acting…`)
- Unavailable tooltip: `Data Not Available — catalog entry pending`

### Accessories
- Picker prefix: `ACCESSORIES`
- Picker default label: `All families`
- Family option format: `{family name} ({N})` (e.g., `ALR (2)`)
- Search label: `Search`
- Search placeholder: `Filter by code or attribute…`
- Selected count: `{N} selected`
- Clear button: `Clear all`
- Loading state: `Loading accessories…`
- Empty filter: `No accessories match the current filter.`
- Family group count: `{N} items` (or `1 item`)
- Item attrs format: `{val1} · {val2} · {val3} · {val4}` (first 4 attrs joined)

### Summary panel
- Card labels: `Valve`, `Actuator`, `Accessories ({N})`
- Valve card name format: `{section.label}` (e.g., `Ball Valve`)
- Actuator card name format: `{model} · {actuator friendly name}` (e.g., `ACT-050D · Pneumatic Rack & Pinion Actuator`)
- Accessory chip: family tag (e.g., `ALR`) + code (e.g., `ARALA001`)

### Footer
- `Local-only tool · no data leaves this machine`

### Placeholder text (accessories card when data file missing)
- Headline: `Data pending`
- Sub: `Please provide the accessories catalog file at data/Accessories/Dashboard accessories.xlsx.`

---

## 14. Responsive specs

### 14.1 Breakpoints

| Breakpoint | Trigger | What changes |
|---|---|---|
| `980px` | `@media (max-width: 980px)` | Workspace grid collapses to 1 column; summary grid → 1 column; accessories toolbar wraps vertically; picker/search become full-width |
| `860px` | `@media (max-width: 860px)` | Picker row stacks vertically; type pickers full-width; main grid (legacy) → 1 column; section-head padding reduced to 16px |
| `720px` | `@media (max-width: 720px)` | Header brand stacks (title above logo) |

### 14.2 At each breakpoint

**Desktop (≥ 980px):**
- Workspace: `1fr 1fr` two-column grid
- Summary: `1fr 1fr` valve + actuator cards side-by-side
- Accessories toolbar: row layout (filter | search | selected count + clear)
- Picker row: side-by-side

**Tablet (860-980px):**
- Workspace: single column (Valves → Actuators → Accessories → Summary)
- Summary grid: single column (Valve card stacked above Actuator card)
- Accessories toolbar: stacks vertically; "selected count + clear" justify-between
- Picker/search inputs: 100% width

**Mobile (< 860px):**
- Picker row: column layout, full-width buttons
- Picker dropdown menus: full width (`left: 0; right: 0`)
- Main grid (legacy `valve-section`): single column
- Section head padding: 16px (was 40px)

**Narrow mobile (< 720px):**
- Header `.brand`: column layout (title above logo, both left-aligned, 12px gap)

---

## 15. Accessibility specs

### 15.1 Focus management

- Every interactive element has a `:focus-visible` rule with a 3px teal-soft ring
  (`box-shadow: 0 0 0 3px var(--c-accent-ring)`)
- Native `<select>`, `<input>`, `<button>` elements preserve native keyboard handling
- Custom dropdown menus (`.type-picker`) close on ESC and outside-click
- Tab order follows DOM order — logical reading sequence (header → picker → workspace cols → accessories → summary → footer)

### 15.2 ARIA & semantic HTML

| Element | Attributes |
|---|---|
| `<nav class="type-picker">` | `data-category="Valves"` |
| `<button class="type-picker-trigger">` | `aria-haspopup="true"`, `aria-expanded="false"` (toggled by JS) |
| `<div class="type-picker-menu">` | `role="menu"` |
| `<button class="type-picker-option">` | `role="menuitem"` |
| Decorative icons (`◐`, `◑`, `+`, `★`, SVG glyphs) | `aria-hidden="true"` |
| `<label>` wrapping checkbox + content | Native click-to-focus + click-to-toggle |
| Accessory list container | `role="list"` |
| Logo `<img>` | `alt="AVCON Controls"` |

### 15.3 Color contrast

All text/background combos meet WCAG AA at minimum:
- Body text `#3a3a3a` on `#fcfcfc` → 11.2:1 (AAA)
- Brand teal `#017E80` on white → 5.46:1 (AA)
- Muted gray `#7A7A7A` on white → 4.69:1 (AA for normal text)
- Subtle gray `#9B9A93` on white → 3.27:1 (AA for large text only) — used only in footer / placeholder text

### 15.4 Non-color signals

Every state change has a non-color signal:
- Selected items: bg fill change AND border color change
- Disabled buttons: `cursor: not-allowed` AND opacity change AND text muted
- Hover: position lift (transform) AND shadow AND color change
- Focus: 3px ring (clearly visible regardless of background)

---

## 16. Browser support

| Browser | Status | Notes |
|---|---|---|
| Chrome / Edge 88+ | ✅ Full support | CSS `:has()`, `aspect-ratio`, custom properties all native |
| Firefox 121+ | ✅ Full support | `:has()` shipped Dec 2023 |
| Safari 15.4+ | ✅ Full support | `:has()` shipped March 2022 |
| IE 11 | ❌ Not supported | No CSS custom properties, no `:has()`, no grid `template-areas` reliable |
| Legacy Edge (pre-Chromium) | ❌ Not supported | Same as IE 11 |

**Required CSS features:**
- Custom properties (`var(--c-*)`)
- CSS Grid + `grid-template-areas`
- `:has()` selector (used to auto-hide column placeholder when section appears)
- `accent-color` (used to color checkboxes teal)
- `appearance: none` (custom select chevron)

**Required JS features:**
- `async`/`await`
- `Map`, `Set`
- `CustomEvent`
- `fetch`
- Template literals

All of the above are ES2017+ and stable in browsers ≥ 4 years old. No transpilation needed.

---

## 17. Build & deployment

### 17.1 Running in dev

```bash
cd "Product Code Finder"
py app/server.py
# OR set VALVE_SELECTOR_NO_BROWSER=1 to suppress auto-open browser
```

App listens on `127.0.0.1:5037`. Press Ctrl+C to stop.

### 17.2 Hot-reload behavior

| Edit type | Requires |
|---|---|
| `*.py` (server, catalog, accessories) | Server restart |
| `*.html` template | Server restart (Flask production mode caches templates) |
| `*.css` | Hard browser refresh (`Ctrl+Shift+R`) |
| `*.js` | Hard browser refresh |
| Data file `*.xlsx`/`*.xlsm` | Server restart (catalogs loaded once at startup) |

### 17.3 Packaging for distribution

Run [build_bundle.bat](build_bundle.bat) to produce a ZIP with:
- `python/` embedded runtime
- `app/`, `data/`, `run.bat`, `README.txt`, `MAINTENANCE.txt`

End users just unzip and double-click `run.bat`. No installation steps.

### 17.4 Customizing for a different brand

To reskin the app with another company's identity, you only need to edit
3 things — the rest follows automatically because everything goes through
CSS variables:

1. **Replace `app/static/avcon-logo.png`** with the new logo (any size; CSS scales to 52px height)
2. **Edit `:root` tokens** in `app/static/styles.css` lines 8-53:
   - `--c-accent` → new brand color
   - `--c-accent-hover` → darker shade
   - `--c-accent-soft` → `rgba(R, G, B, 0.10)` of new brand color
   - `--c-accent-ring` → `rgba(R, G, B, 0.22)` of new brand color
   - Font families if desired
3. **Edit `index.html`** title line 17:
   - `BV–BFV–Actuator–Accessory` → new product name
   - `Product Code Finder` → new tagline

That's it. The entire interface re-brands with those 3 edits.

---

## Appendix A — Quick visual mockup of every state

### Page on first load (empty state)
```
┌────────────────────────────────────────────────────────────────────────────┐
│ BV–BFV–ACTUATOR–ACCESSORY                              [AVCON LOGO 52px]   │
│ Product Code Finder                                                        │
│ 49,289 AVCON SKUs. Infinite Specs. One Click.                              │
├────────────────────────────────────────────────────────────────────────────┤
│ [VALVES │ Choose valve type ▾]    [ACTUATORS │ Choose actuator type ▾]    │
├────────────────────────────────────────────────────────────────────────────┤
│         Pick a type from the menus above to start.                         │
├──────────────────────────────────┬─────────────────────────────────────────┤
│ │ ◐ Valves                       │ │ ◑ Actuators                          │
│   Pick a valve type from the     │   Pick an actuator type, or use a     │
│   menu above.                    │   valve's recommendation.              │
├──────────────────────────────────┴─────────────────────────────────────────┤
│ │ + Accessories                                       162 items · 13 fams │
│   [ACCESSORIES │ All families ▾]    [Search: …………]              0 selected│
│   ┌──────────────────────────────────────────────────────────────────┐    │
│   │  ALR  (2 items)                                                    │    │
│   │  ☐ ARALA001  Avcon · ALR · Aluminum Pressure Die · 1/4" BSP       │    │
│   │  ☐ ARALA002  Avcon · ALR · Aluminum Pressure Die · 1/4" BSP       │    │
│   │  BKT  (8 items)                                                    │    │
│   │  ☐ BKCSADEN  Avcon · Carbon Steel (CS) · …                        │    │
│   │  ... (scrollable, max-height 480px)                                │    │
│   └──────────────────────────────────────────────────────────────────┘    │
├────────────────────────────────────────────────────────────────────────────┤
│ (summary panel hidden until first selection)                               │
├────────────────────────────────────────────────────────────────────────────┤
│              Local-only tool · no data leaves this machine                 │
└────────────────────────────────────────────────────────────────────────────┘
```

### After picking a Ball Valve + actuator + 3 accessories
```
┌────────────────────────────────────────────────────────────────────────────┐
│ (header unchanged)                                                         │
├────────────────────────────────────────────────────────────────────────────┤
│ [VALVES │ Ball Valve ▾]            [ACTUATORS │ Rack & Pinion ▾]          │
├──────────────────────────────────┬─────────────────────────────────────────┤
│ │ ◐ Valves                       │ │ ◑ Actuators                          │
│ │ Ball Valve                     │ │ Pneumatic Rack & Pinion             │
│   3,892 valve SKUs               │   1,620 actuator SKUs                  │
│   Selection ▾▾▾▾▾▾▾▾▾▾▾▾▾▾▾   │   Selection ▾▾▾▾▾▾▾                  │
│   Your Match                     │   Your Match                            │
│   Here's your match!             │   Here's your match!                    │
│   ┌──────┐ ┌──────────────┐      │   ┌──────┐ ┌────────────┐              │
│   │BVC   │ │ CatCode      │      │   │ Code │ │ Model      │              │
│   │2030F1│ │ 2030F1.../A1 │      │   │RPAD05│ │ ACT-050D   │              │
│   └──────┘ └──────────────┘      │   └──────┘ └────────────┘              │
│   ┌──────┐ ┌──────────────┐      │                                          │
│   │BTO 5 │ │ FOS = 7.5    │      │                                          │
│   └──────┘ └──────────────┘      │                                          │
│   RECOMMENDED ACTUATOR           │                                          │
│   Option 1 — Pneumatic           │                                          │
│   [ACT-050D] [ACT-063SR07]       │                                          │
│   [ACT-050SR12] [ACT-063SR05]    │                                          │
│   Option 2 — Electric            │                                          │
│   [EA-21/D] [EA-21/E]            │                                          │
├──────────────────────────────────┴─────────────────────────────────────────┤
│ │ + Accessories  (3 selected)                                              │
│   ... list with 3 ticked items ...                                          │
├────────────────────────────────────────────────────────────────────────────┤
│ ★ YOUR PRODUCT CODE IS                                                     │
│ ┌──────────────────┐  ┌──────────────────────────────┐                     │
│ │ VALVE            │  │ ACTUATOR                     │                     │
│ │ 2030FC0001       │  │ RPAD0501                     │                     │
│ │ Ball Valve       │  │ ACT-050D · Pneumatic R&P     │                     │
│ └──────────────────┘  └──────────────────────────────┘                     │
│ ┌──────────────────────────────────────────────────────────┐               │
│ │ ACCESSORIES (3)                                          │               │
│ │ [ALR ARALA001] [BKT BKCSADEN] [FRG FRALAOBN]            │               │
│ └──────────────────────────────────────────────────────────┘               │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix B — Design principles in one paragraph

**Industrial calm.** Restrained palette (one brand teal, neutral grays, no
reds in the live UI), modest typography (Roboto family throughout), minimal
shadows, sharp-cornered chrome (`2-6px` radius), short 180ms animations.
Everything serves the cascade — the eye flows from valve picker → result →
recommended actuator chips → actuator cascade → "Your Product Code is"
summary, with no decorative noise to distract from the data. Cards are
flat, text is information-dense without being cluttered, color signals
state changes (gray → teal on selection, amber on missing data) but never
alarms. The whole interface is designed to disappear behind the catalog —
the user's attention should land on Excel data rendered as web UI, not on
chrome.

---

**End of document.** Anything not captured here, consult the source:
- [app/static/styles.css](app/static/styles.css)
- [app/templates/index.html](app/templates/index.html)
- [app/static/app.js](app/static/app.js)
