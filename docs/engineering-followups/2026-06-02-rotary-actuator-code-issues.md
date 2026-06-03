# Engineering follow-up: Electrical Rotary actuator code issues

**Date:** 2026-06-02
**Source of truth:** `data/Actuator/Electrical Actuator/Electrical Actuator Rotory Data Sheet Structure - 09.12.2025.xlsx`
**Corrected reference:** `Actuator.xlsx` (kept in this folder) — a combined working file that holds the corrected/missing codes.

Found while cell-reviewing `Actuator.xlsx` before retiring it. These are defects in
the **authoritative rotary datasheet**, not app bugs — the app faithfully loads what
the datasheet contains (96 rows, but only **94 distinct codes** because of the two
collisions below).

## 1. Duplicate codes (one code used for two different actuators)

The `EA-21/D` (ONF) and `EA-21/E` ("with Potentiometer") variants share a single code
in two cases:

| Code (reused) | Row A | Row B |
| --- | --- | --- |
| `E021GN01` | EA-21/D · 110 VAC 50 Hz · ONF | EA-21/E · 110 VAC 50 Hz · with Potentiometer |
| `E021GJ01` | EA-21/D · 24 VAC 50 Hz · ONF | EA-21/E · 24 VAC 50 Hz · with Potentiometer |

Effect in the app: selecting Model `EA-21/E` at those voltages resolves to the
**wrong code** (`E021GN01` / `E021GJ01`, which belong to the `EA-21/D` ONF variant).

## 2. Missing variant

`EA-21/E` · **110 VAC 60 Hz** · with Potentiometer is **absent** from the datasheet
(only `E021GX01` = `EA-21/D` 110 VAC 60 Hz ONF exists).

## 3. What `Actuator.xlsx` already corrects

- `E021GN02` = EA-21/E · 110 VAC 50 Hz · with Potentiometer (the correct code for the
  `E021GN01` collision's Row B), with full specs.
- `E021GX02` = EA-21/E · 110 VAC 60 Hz · with Potentiometer (the missing variant).
- **Not corrected:** the `E021GJ01` collision (24 VAC 50 Hz) — `Actuator.xlsx` has no
  distinct code for the EA-21/E 24 VAC 50 Hz variant. Engineering needs to assign one.

## Recommended fix (in the authoritative datasheet)

1. Re-code the `EA-21/E` 110 VAC 50 Hz row from `E021GN01` → `E021GN02`.
2. Re-code the `EA-21/E` 24 VAC 50 Hz row from `E021GJ01` → a new distinct code.
3. Add the missing `EA-21/E` 110 VAC 60 Hz row as `E021GX02`.

Once the datasheet is corrected, the app picks the fixes up automatically (it reads
that file directly) — no app code change needed. The ONF/Potentiometer split is
already encoded in the Model suffix (`/D` vs `/E`), so no extra cascade field is
needed; only the codes need cleaning.
