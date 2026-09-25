# Engineering follow-up: Solenoid Valve _Updated5

**Date:** 2026-09-25
**Source:** `data/Accessories/Solenoid Valve_Updated5.xlsx` (sheet `Sheet1`)
**Compared to:** `data/Accessories/Solenoid Valve_Updated4.xlsx`

Ingested as-is (standing direction: trust AVCON). Headers and the `Coil Logic`
sheet are unchanged. No existing rows were edited. The loader still uses
newest-wins on substring `Solenoid Valve`; `merge_all` stays off.

**What changed in the drop:**
- 89 rows → **96 rows** (95 distinct codes)
- **7 new codes** added; 0 removed

New codes: `SR484A3RWR04`, `SR484A3RFK01`, `SR327C0RFK01`, `S9210B4SWK01`,
`S9210B4SWK02`, `S9230C5SWK01`, `S9230C5SWK02`.

Source typos (`Catlouge`, `Piolt operated`, `Namur Mouting`) are kept verbatim.

## 1. `SR432A3RWK02` still used for two different products (pre-existing)

Unchanged from `_Updated2` / `_Updated4`. Two rows share the code (BSP vs NPT
end connection). The sheet therefore has **96 rows but 95 distinct codes**.

**Requested fix:** assign a distinct code to one of the two end-connection
variants.

## 2. `SR484A3RWR02` SERIES says NPT, End Connection says BSP (pre-existing)

Unchanged from `_Updated4`. Loaded verbatim.

**Requested fix:** make columns 2, 3, and 11 agree.

## 3. `S9210B4SWK01` / `S9210B4SWK02` SERIES says NPT, End Connection says BSP (new)

| Code | SERIES | End Connection |
| --- | --- | --- |
| `S9210B4SWK01` | `9210B15/CF8M/S6/V/NPT` | BSP Screwed (Female) |
| `S9210B4SWK02` | `9210B25/CF8M/S6/V/NPT` | BSP Screwed (Female) |

Combined Catalogue also contains `/NPT`. Same class of mismatch as
`SR484A3RWR02`.

**Effect in the app:** both rows are shown verbatim, so SERIES and End
Connection disagree.

**Requested fix:** confirm NPT vs BSP and make columns 2, 3, and 11 agree.

## 4. `S9230C5SWK01` port size uses a ½ character

Column 9 `Body/Port size` is `½" /16 mm` (U+00BD VULGAR FRACTION ONE HALF),
with no space after `/`. Sibling `S9230C5SWK02` is `1" / 25mm`. Loaded
verbatim.
