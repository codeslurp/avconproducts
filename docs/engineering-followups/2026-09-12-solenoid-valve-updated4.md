# Engineering follow-up: Solenoid Valve _Updated4

**Date:** 2026-09-12
**Source:** `data/Accessories/Solenoid Valve_Updated4.xlsx` (sheet `Sheet1`)
**Compared to:** `data/Accessories/Solenoid Valve_Updated3.xlsx`

Ingested as-is (standing direction: trust AVCON). Headers and the `Coil Logic`
sheet are unchanged. The loader still uses newest-wins on substring
`Solenoid Valve`; `merge_all` stays off.

**What changed in the drop:**
- 75 rows → **89 rows** (88 distinct codes)
- **15 new codes** added
- **1 recode:** `R487A2SEK01` → `SR487A2SEK01` (same attributes, `S` prefix)
- **11 existing R384/R484 rows:** `SERIES` / Combined Catalogue `/AD/` → `/AL/`
  (body material was already Aluminium). `SR384A7SWK01` Coil terminals also
  changed `Din Connector 43650` → `Screwed`

Source typos (`Catlouge`, `Piolt operated`, `Namur Mouting`) are kept verbatim.

## 1. `SR432A3RWK02` still used for two different products (pre-existing)

Unchanged from `_Updated2` / `_Updated3`. Two rows share the code:

| Col | Row A | Row B |
| --- | --- | --- |
| 3 `SERIES` | `R432E06/AD/S4/BN/BSP` | `R432E06/AD/S4/BN/NPT` |
| 11 `End Connection` | BSP Screwed (Female) | NPT Screwed (Female) |

All other columns match. The sheet therefore has **89 rows but 88 distinct
codes**.

**Effect in the app:** both rows are listed; picking by code cannot distinguish
the BSP variant from the NPT one.

**Requested fix:** assign a distinct code to one of the two end-connection
variants.

## 2. `SR484A3RWR02` SERIES says NPT, End Connection says BSP (new in this drop)

| Col | Value |
| --- | --- |
| 1 Code | `SR484A3RWR02` |
| 2 Combined Catalogue | `R484E06/AL/S4/BN/NPT-M36-RD-MS/WP67/H-230 VAC 50 Hz` |
| 3 SERIES | `R484E06/AL/S4/BN/NPT` |
| 11 End Connection | BSP Screwed (Female) |

Sibling new codes `SR484A3RWR01` / `RWR03` are BSP in both SERIES and End
Connection. This row is the only new NPT-tagged series with a BSP end-connection
cell.

**Effect in the app:** the row is shown verbatim, so SERIES and End Connection
disagree.

**Requested fix:** confirm whether the end connection is NPT or BSP and make
columns 2, 3, and 11 agree.
