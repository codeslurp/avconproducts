# Engineering follow-up: 2030F / 2060F / 2090F actuator columns

**Date:** 2026-10-18
**Sources (newest-wins):**
- `data/Valve/Pune/Ball Valve Data Set/2030F BV NEW CODEING_Updated.xlsx`
- `data/Valve/Pune/Ball Valve Data Set/2060F BV NEW CODEING_Updated.xlsx`
- `data/Valve/Pune/Ball Valve Data Set/2090F BV NEW CODEING_Updated.xlsx`

Same SKU lists as the May files (1,344 / 504 / 840). Actuator columns 49–61
were rewritten: 3.5/4/5.5 bar labels, NC/NO on Fail-Close / Fail-Open, and
many former `0`/blank slots filled with `ACT-*` models.

**2070F was not in the drop.** It still uses `2070F BV NEW CODEING.xlsx` and
the old 49–59 → 111–121 alt map.

## Mapping

| Source col (Updated files) | Dest on metal master |
| --- | --- |
| 49–51 DA @ 3.5/4/5.5 bar | 100–102 (overwrites dashboard) |
| 52–54 FSC NC @ 3.5/4/5.5 | 103–105 |
| 55–57 FSO NO @ 3.5/4/5.5 | 106–108 |
| 59–60 Electrical 1 / 2 | 109–110 |
| 58 Linear Actuator (5–6 Bar) | 122 (empty in this drop) |
| 61 Manual | 123 (empty in this drop) |

Old layout put Electric in col 58. Using that map on the Updated files would
have parked Linear (empty) on the Electric slot.

## Still in the source

- **2060F / 2090F:** `#N/A` on a block of rows (84 / 112) — skipped at resolve.
- **Linear and Manual columns are blank** on every row of all three files.

Pressure slots (DA / Fail-Close / Fail-Open @ 3.5/4/5.5 bar) now each get a
chip even when the model repeats — same as Double Acting. Example
`2090FC0002`: FSC 3.5 and 4 bar are both `ACT-063SR06`, but both chips show.
