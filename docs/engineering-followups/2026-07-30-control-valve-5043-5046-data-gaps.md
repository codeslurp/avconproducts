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

## 2. 5066A ships every product twice under two bare codes (pre-existing)

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
