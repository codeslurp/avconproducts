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

## 2. RESOLVED — 5066A duplication, fixed same day

**Status: fixed 2026-07-30** by the re-drop
`Control Valve Data for New Structure 5066A 3W BELLOW SEAL.xlsx` (no R suffix),
now live. 5066A is 320 rows / 320 distinct products / one code each, verified 0
duplicate groups. With this, the **whole control valve catalog is 0 ambiguous**
for the first time — the invariant was violated by 320 rows until now.

The original report is kept below for the record, followed by two consequences
of the fix that still need attention (items 3 and 4).

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

## 3. 5066A lost all four spec columns in the de-duplicated re-drop

The fix in item 2 also blanked every spec column that `_R2` populated on all
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

## 4. 160 of the 320 retained 5066A codes now mean a different valve

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
