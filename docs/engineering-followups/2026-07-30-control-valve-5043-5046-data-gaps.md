# Engineering follow-up: Control Valve 5043A-5046A R1, and a 5066A duplication

**Date:** 2026-07-30
**Sources:**
- `data/Valve/Pune/Control Valve Data Set/Control Valve Data for New Structure_5043A 5044A 5045A 5046A _R1- 14.07.2026.xlsx`
- `data/Valve/Pune/Control Valve Data Set/Control Valve Data for New Structure 5066A 3W BELLOW SEAL_R2.xlsx`

The 5043A-5046A drop was ingested as-is (standing direction: "trust AVCON").
Item 2 below is a **pre-existing** defect found while validating the drop; it is
unrelated to the new series and is already live.

## 1. 5043A-5046A ship no Fail-Safe actuator models

The drop is otherwise complete: all 53 non-spec canonical columns are present
verbatim in all four tabs, and all 1,040 bare codes are unique and disjoint from
the existing six series.

But the spec region arrives as unnamed `Additional Specification 1-5`, and slots
**1 through 10 are empty in all 1,040 rows**. The two columns that matter are:

| Canonical column | 5012A | 5043A-5046A |
| --- | --- | --- |
| Fail Safe Close / A-Port Close | 10,801 / 10,801 | **0 / 1,040** |
| Fail Safe Open / B-Port Close | 10,801 / 10,801 | **0 / 1,040** |

**Effect in the app:** the two "recommended actuator" cards resolve empty, so
that section is hidden for these four series. Everything else — cascade,
codes, materials, dimensions, Stroke — works normally. The 13-field base cascade
resolves all 1,040 SKUs with **0 ambiguous**.

For the avoidance of doubt: `Thrust (KN)`, `Torque (Nm)`, `Mounting PCD` and
`Stem Diameter` are empty here too, but they are empty **catalog-wide** —
including on 5012A — so they are not a gap introduced by this drop.

**Requested fix:** supply the Fail-Safe Close/Open MSD actuator models for
5043A/5044A/5045A/5046A in R2, in named columns as per the 5012 R2_Updated
format.

## 2. RESOLVED — 5066A duplication, fixed properly by R3

**Status: fixed 2026-08-02** by
`Control Valve Data for New Structure 5066A 3W BELLOW SEAL_R3.xlsx`, now live.

It took two attempts, and the difference matters:

| | Rows | Distinct products | Verdict |
| --- | --- | --- | --- |
| `_R2` | 640 | 320 | the defect |
| interim (no suffix), 2026-07-30 | 320 | 320 | **wrong** — deleted 320 real products, remapped 160 codes |
| **`_R3`, 2026-08-02** | **640** | **640** | **correct** |

R3 supplies the attribute that was actually missing rather than deleting rows:
**Face to Face** differs on exactly 320 rows — `5066AD0001` is
`DIN EN 558 SERIES-1 #150`, `5066AD0006` is `ISA 75.08.01 #150`. They were never
duplicates; `_R2` mislabelled their face-to-face standard. Face to Face is a
cascade field and is in 5066A's `cascade_overrides`, which is exactly why the
640 now resolve unambiguously.

R3 vs `_R2` changes ONLY Face to Face (320 rows) and the four spec columns
(blanked, restored — see item 3). No code changes meaning, so **item 4 below is
void**: the quote-reconciliation concern was an artefact of the interim file and
no longer applies.

The **whole control valve catalog is now 0 ambiguous**, at the full 18,721 SKUs.

The original report is kept below for the record.

### Original report



`5066A` (3-way bellow seal) has **640 rows but only 320 distinct products**.
Every product appears twice, under two different bare valve codes that are
identical in **every other column** — all 58 of them.

The pairing is systematic, at an offset of +5:

| Code A | Code B |
| --- | --- |
| 5066AD0001 | 5066AD0006 |
| 5066AD0002 | 5066AD0007 |
| 5066AD0003 | 5066AD0008 |
| 5066AD0004 | 5066AD0009 |

…and so on, across all 320 pairs and all 8 size sub-series (80 rows each).

**This predates the 5043A-5046A drop.** Confirmed by running the same check
against the previously deployed `docs/data/control_valve.json`: 320 ambiguous
rows before, 320 after — byte-for-byte the same defect, currently live.

**Effect in the app:** the cascade cannot distinguish the two members of a pair
(they differ only in the code the cascade is trying to *produce*), so selecting
any 5066A configuration always resolves to whichever row is first. **Half of
5066A's 640 SKUs are unreachable.**

Not corrected in code: there is no way to tell from the data which code is
canonical, or what attribute was meant to distinguish them. Pinned at exactly
320 pairs by `test_5066a_duplicate_codes_are_unchanged` in
`tests/test_control_valve_5043_5046.py`, so any change is noticed.

**Requested fix:** either (a) supply the attribute that distinguishes the two
variants so the cascade can reach both, or (b) withdraw the duplicate code
block if it was an accidental duplication in the R2 export.

*Pune chose (b), and compacted the code space at the same time. See below.*

## 3. RESOLVED (restored locally) — 5066A spec columns

**Status: restored 2026-08-02**, but the underlying request to Pune stands.

`_R3` still ships the spec region blank. Rather than lose the data, all four
columns are now restored from `_R2` by the `enrich` step in
`tools/consolidate_control_valve.py`, joined on bare valve code — the same
mechanism that restores 5016's B-Port column. All four report 640/640 filled
(`19 bar`, `MSD-200 D`, `MSD-200 D`, `2.1 bar`), so 5066A keeps its actuator
cards.

This is safe because `_R3` and `_R2` share an identical 640-code set and
identical product identity per code apart from Face to Face: each code gets back
exactly what AVCON published for **that code**, and because `_R2` gave both
members of every former pair the same actuator, the Face-to-Face correction
cannot change which actuator was assigned. (It would **not** have been safe
against the interim file, where 160 codes had been remapped.)

Guarded by `test_5066a_spec_columns_restored_from_r2`.

**Still requested:** ship these four columns populated in the next 5066A
revision, so the app stops depending on a back-fill from a superseded file.

### Original report

The interim fix blanked every spec column that `_R2` populated on all
640 rows:

| Canonical column | `_R2` | de-duplicated re-drop |
| --- | --- | --- |
| Max Shut-off Pressure | `19 bar` — 640/640 | **0/320** |
| Fail Safe Close / A-Port Close | `MSD-200 D` — 640/640 | **0/320** |
| Fail Safe Open / B-Port Close | `MSD-200 D` — 640/640 | **0/320** |
| Control Pressure | `2.1 bar` — 640/640 | **0/320** |

**Effect in the app:** 5066A no longer shows recommended actuator cards, the
same state as 5043A-5046A (item 1). Everything else works.

The spec data was **not** carried over from `_R2`. There is an existing
mechanism for exactly that (the `enrich` step that restores 5016's B-Port
column), but it joins on bare valve code, and item 4 makes that unsafe here: it
would attach an actuator sized for the old valve to a different valve.

**Requested fix:** re-issue 5066A with the Max Shut-off, Fail Safe A/B Port
Close and Control Pressure columns populated, alongside the de-duplicated codes.

## 4. VOID — 160 remapped 5066A codes

**Status: no longer applicable as of 2026-08-02.** This was caused by the
interim 320-row file, which was live for roughly two days. `_R3` keeps every
code's `_R2` product identity (only Face to Face changed), so no code means a
different valve and **no quote reconciliation is needed**.

Kept below for the record only.

### Original report

Compacting the code space reassigned products to codes. Half the retained codes
describe a different valve than they did under `_R2`.

Worked example — `5066AD0006`:

| | `_R2` | re-drop |
| --- | --- | --- |
| Characteristics | On-Off | **Linear** |

The product `5066AD0006` now denotes was previously carried by `_R2` codes
`5066AD0011` and `5066AD0016`.

Columns that changed on those 160 rows: Characteristics, End Connections, Face
to Face, Flow Direction, Flange Dimensions, Flange Drilling, Pressure Rating,
Body Test Pressure. The Catalogue code changed on **all 320** (it gains an
`/MTM/` segment).

**Commercial impact — for Sales, not engineering:** any quotation or order
already raised against a 5066A bare code may no longer describe the valve that
code now resolves to. Codes issued before 2026-07-30 should be re-checked
against the old `_R2` definitions, which remain on disk at
`data/Valve/Pune/Control Valve Data Set/Control Valve Data for New Structure 5066A 3W BELLOW SEAL_R2.xlsx`.

**Requested confirmation:** that the renumbering was intentional and that
previously-issued 5066A codes have been reconciled.
