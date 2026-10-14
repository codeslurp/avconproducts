# Engineering follow-up: Solenoid Valve _Updated6

**Date:** 2026-10-14
**Source:** `data/Accessories/Solenoid Valve_Updated6.xlsx` (sheet `Sheet1`)
**Compared to:** `data/Accessories/Solenoid Valve_Updated5.xlsx`

Ingested as-is (standing direction: trust AVCON). Headers and the `Coil Logic`
sheet are unchanged. No existing shared-code rows were edited. The loader still
uses newest-wins on substring `Solenoid Valve`; `merge_all` stays off.

**What changed in the drop:**
- 96 rows → **101 rows** (100 distinct codes)
- **18 added, 13 removed**

Recodes:
- 12× `S9321C3*` / `S9322C3*` → `S9321S3*` / `S9322S3*` (body CF8M → SS316)
- `S472S3RWK01` → `SR472S3RWK01` (`S` prefix)

Genuinely new: `S9321S3RFK01`, `S9350B4SWR01`, `SR472S3RFK01`,
`S9440C4SWR01`, `S9442C4SWK01`.

## 1–3. Pre-existing, unchanged

- `SR432A3RWK02` still used for two products (BSP vs NPT) — 101 rows, 100
  distinct codes
- `SR484A3RWR02` SERIES NPT / End Connection BSP
- `S9210B4SWK01` / `S9210B4SWK02` SERIES NPT / End Connection BSP

## 4. `S9321S3SWK05` / `SWR05` / `SWN02` SERIES is 9322 (new)

Combined Catalogue is `9321B15…` (normally closed) but SERIES is
`9322B15…` (normally open). TYPE still says Normally Closed.

**Requested fix:** SERIES should be `9321B15…` to match the code and catalogue.

## 5. `S9322S3RFN02` catalogue still says CF8M (new)

Combined Catalogue: `9322B15/CF8M/S6/BN/BSP-…`
SERIES and Body Material: SS316 (`S6`).

**Requested fix:** replace `/CF8M/` in the catalogue with `/S6/` (or the
intended body).

## 6. `SR472S3RFK01` body vs series disagree (new)

SERIES is `R472E06/S6/S6/BN/NPT` (SS316) but Body Material is Aluminium.
End Connection is NPT.

**Requested fix:** confirm body material and make SERIES / Body Material agree.
