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
