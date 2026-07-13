#!/usr/bin/env python
"""Consolidate the AVCON 'New Structure' R2 per-series Control-Valve files into a
single `Control Valve Dashboard_V2.xlsx` shaped EXACTLY like the retired
`Dashboard_V1`, so the existing positional `CONTROL_VALVE` loader
(`app/catalog.py`) reads it with NO code change.

Why this exists
---------------
The live engine addresses catalog columns by 1-based POSITION (see
`ValveTypeConfig` in app/catalog.py). The drop is split across 4 files /
6 sheets with a different column order and no Power-Query "name" column. This
script normalises each sheet to the canonical Dashboard_V1 column order, re-adds
the name column at position 0, concatenates all six series into one
`Control Valve` sheet, and writes the V2 workbook.

R1 -> R2 change (2026-06-11)
----------------------------
R2 keeps every bare code, row count, and *exposed* column value identical to R1
(verified by cell-level diff). Its only substantive change: the first four
"Additional Specification" slots (source positions 43-46) were given real,
*series-varying* names -- 5012 uses "Fail Safe Close"/"Open"; the 3-way/double
families use "Fail Safe A/B Port Close". Because the engine reads by position
and a consolidated sheet has one header row, this script normalises those
slots to ONE canonical header set BY POSITION (see SPEC_SLOT_NAMES), guarded by
the stable anchor columns (43 ~ shut-off, 46 ~ control). These columns are
now surfaced in the control-valve detail panel (catalog.py detail_columns 45-49).

R2 re-drop (2026-06-14)
-----------------------
5012A/B split Control Pressure by fail-safe mode: source col 46 became the
"...Fail Safe Close condition" value and source col 47 (previously the empty
"Additional Specification 5") became the "...Open condition" value. We promote
source position 47 to a 5th canonical spec slot, "Control Pressure (Fail Safe
Open)" — populated only on 5012A/B, blank on the other series (their col 47 is a
confirmed-empty Additional Spec slot). 5061A also relabelled its fail-safe
headers Close/Open (cosmetic; handled by the same positional normalisation).

It is deliberately strict: it FAILS (non-zero exit, no file written) if any
canonical column is missing from a source sheet or the spec-slot anchors are not
found, and prints a per-series add/remove report against the archived V1
baseline so nothing changes silently.

Run:  py tools/consolidate_control_valve.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

CV_DIR = (
    Path(__file__).resolve().parent.parent
    / "data" / "Valve" / "Pune" / "Control Valve Data Set"
)
SRC_DIR = CV_DIR / "source_R2"
OUT = CV_DIR / "Control Valve Dashboard_V2.xlsx"

# R2 named the "Additional Specification" slots (source positions 43+, 0-based)
# with real but series-varying labels. The engine reads by position, so we
# collapse them to ONE canonical header set keyed by position. Order MUST match
# source positions 43,44,45,46,47. Surfaced in the detail panel via catalog.py
# CONTROL_VALVE.detail_columns (1-based cols 45-49).
#
# 2026-06-14 re-drop: 5012A/B split Control Pressure by fail-safe mode — src 46
# became "Control Pressure when Fail Safe Close condition" and src 47 (was the
# empty "Additional Specification 5") became "...Open condition". All other
# series keep a single generic Control Pressure at 46 and an empty slot at 47
# (verified 0% filled), so promoting 47 to a real column only adds data for 5012
# and leaves the rest blank — no data loss.
SPEC_SLOTS = (43, 44, 45, 46, 47)
SPEC_SLOT_NAMES = [
    "Max Shut-off Pressure",            # src 43 (was Additional Specification 1)
    "Fail Safe Close / A-Port Close",   # src 44 (was Additional Specification 2)
    "Fail Safe Open / B-Port Close",    # src 45 (was Additional Specification 3)
    "Control Pressure",                 # src 46 (was Additional Specification 4)
    "Control Pressure (Fail Safe Open)",  # src 47 (was Additional Specification 5);
                                          # populated only on 5012A/B, blank elsewhere
]

# Stable anchor positions present in EVERY series (used to guard the positional
# rename — do NOT key these off SPEC_SLOTS, which now reaches the series-varying
# col 47). 43 ~ shut-off, 46 ~ control pressure: both present in all six series.
SPEC_ANCHOR_SHUTOFF = 43
SPEC_ANCHOR_CONTROL = 46

# Canonical data-column order = Dashboard_V1 'Control Valve' header row, positions
# 1..58 (position 0 is the Power-Query name column, re-added per row below). The
# engine reads by 1-based position, so THIS ORDER IS THE CONTRACT. Cost columns
# (the last 4) are kept at their positions but the loader excludes them from the
# cascade and public JSON, exactly as it did for V1.
CANON = [
    "Bare Valve Code", "Catlouge", "Make", "Series", "Valve Size Inch",
    "Body Material", "Trim Material", "Seat Material", "Characteristics",
    "End Connections", "Valve Type", "Design Standard", "Face to Face",
    "Port Size (mm)", "No. Of Ports", "Valve Kv (m³/hr)", "Body Style",
    "Flow Direction", "Bonnet Material", "Type Of Bonnet", "Stem Material",
    "Plug Type", "Gland Packing", "Body Packing", "Flange Dimensions",
    "Flange Drilling", "Pressure Rating", "Operating Temp Range ( Deg C)",
    "Hardware", "Valve Paint", "Testing Standard", "Leakage Class",
    "Body Test Pressure (barg)", "Body Test Media",
    "Seat Leakage Test Pressure (barg)", "Seat Leakage Test Media",
    "Product Group", "Certification", "Thrust (KN)", "Torque (Nm)",
    "Mounting PCD", "Stroke (mm)", "Stem Diameter",
    # positions 43-47: R2 named spec slots (normalised by position, see SPEC_SLOTS).
    # Position 47 (formerly "Additional Specification 5") now carries the 5012A/B
    # fail-safe-open control pressure; blank for the other series.
    "Max Shut-off Pressure", "Fail Safe Close / A-Port Close",
    "Fail Safe Open / B-Port Close", "Control Pressure",
    "Control Pressure (Fail Safe Open)", "Additional Specification 6",
    "Additional Specification 7", "Additional Specification 8",
    "Additional Specification 9", "Additional Specification 10",
    "Bare Valve Weight (kg)", "BOM Cost Rate (INR)",
    "Manufacturing Cost Rate (INR)", "Sale Cost Rate (INR)", "Offer Rate (INR)",
]

# (filename, sheet, series-tag) — the R2 per-series drop. 5016A/5016B were
# superseded by an R4 re-drop (2026-07-05) and are ingested separately from
# R4_FILE below; they are NO LONGER read from source_R2.
SOURCES = [
    ("Control Valve Data for New Structure_5012A-B-R2.xlsx", "5012A CV ", "5012A"),
    ("Control Valve Data for New Structure_5012A-B-R2.xlsx", "5012B CV", "5012B"),
    ("Control Valve Data for New Structure_5061A-01.01.26_R2.xlsx", "5061A CV ", "5061A"),
    ("Control Valve Data for New Structure 5066A 3W BELLOW SEAL_R2.xlsx", "5066A CV ", "5066A"),
]

# R4 re-drop for 5016A/5016B (2026-07-05), then RE-DROPPED as "R4_Updated"
# (2026-07-12). The original R4 shipped a single "working" tab with a leading
# name column and TWO Fail-Safe MSD columns ("Fail Safe Close"/"Fail Safe Open").
# R4_Updated reshapes the SAME 1920 SKUs into two per-series tabs ("5016A CV "/
# "5016B CV", no leading name column) plus a "Logic" documentation sheet.
# Verified by cell-level diff (2026-07-12): across the 53 shared columns NOTHING
# changed. The only substantive changes are in the Fail-Safe spec region:
#   • Old "Fail Safe Close" (MSD models) was renamed to "A Port Close / B Port
#     Close" — values IDENTICAL (verified equal on all 1920 rows). We map it to
#     canonical "Fail Safe Close / A-Port Close", so the close-side MSD card is
#     unchanged.
#   • Old "Fail Safe Open" (MSD models) was REMOVED — the new file blanks that
#     slot (now a generic empty "Additional Specification 2"; its MSD values
#     appear in no new column). Per user direction (2026-07-12: "ingest as-is,
#     trust AVCON") we leave canonical "Fail Safe Open / B-Port Close" blank.
#     Consequence: the "Normally Open" MSD recommended-actuator card no longer
#     populates for 5016 (it did under the original R4). This is intentional.
#   • As before, R4 carries no numeric "Max Shut-off Pressure" / "Control
#     Pressure" values, so those canonical slots stay blank for 5016.
R4_FILE = "Control Valve Data for New Structure 5016A-B_24.12.2025_R4_Updated.xlsx"
# per-series tab name -> series tag (R4_Updated has one tab per series, no
# leading name column; the sheet name carries the series).
R4_SHEETS = {"5016A CV ": "5016A", "5016B CV": "5016B"}
# CANON spec-slot names that R4_Updated does NOT provide verbatim, and how to
# fill each from the per-series tab (None -> leave blank).
R4_SPEC_MAP = {
    "Max Shut-off Pressure": None,
    "Fail Safe Close / A-Port Close": "A Port Close / B Port Close",
    "Fail Safe Open / B-Port Close": None,   # removed in R4_Updated (was "Fail Safe Open")
    "Control Pressure": None,
    "Control Pressure (Fail Safe Open)": None,
}

NAME_COL = "Control Valve"  # position-0 padding (engine ignores its content)
SHEET = "Control Valve"     # must contain marker "Control Valve" (substring match)


def _norm(s) -> str:
    return str(s).strip()


def _baseline_v1() -> pd.DataFrame | None:
    """Read the V1 baseline (archived, or still in root) for the delta report.
    Returns a DataFrame indexed by Bare Valve Code, or None if unavailable."""
    candidates = list((CV_DIR / "archive").glob("*.xls*")) + list(
        CV_DIR.glob("Control Valve Dashboard_V1.xls*")
    )
    candidates = [p for p in candidates if not p.name.startswith("~$")]
    if not candidates:
        return None
    path = candidates[0]
    try:
        raw = pd.read_excel(path, sheet_name="Control Valve", header=None, dtype=object)
    except Exception as e:  # locked, missing sheet, etc. — report is optional
        print(f"  [warn] could not read V1 baseline {path.name}: {e}")
        return None
    hdr = [_norm(x) for x in raw.iloc[0].tolist()]
    df = raw.iloc[1:].copy()
    df.columns = hdr
    df = df[df["Bare Valve Code"].notna()]
    df = df[df["Bare Valve Code"].astype(str).str.strip().ne("")]
    df = df[df["Bare Valve Code"].astype(str).str.strip() != "Bare Valve Code"]
    return df


def _r4_5016_frames(base_codes: set[str] | None) -> tuple[list[pd.DataFrame], bool]:
    """Build the 5016A/5016B canonical frames from the R4_Updated per-series tabs.

    R4_Updated ships one tab per series ("5016A CV "/"5016B CV") with NO leading
    name column (the sheet name carries the series), so we read each tab directly
    rather than splitting a single working tab by a tag column.

    Returns (frames, ok). ok is False if an expected tab or canonical column is
    missing — the caller aborts without writing V2, same as the R2 path. Prints
    per-series report lines in the SOURCES-loop format."""
    path = CV_DIR / R4_FILE
    if not path.is_file():
        print(f"[FAIL] 5016 R4 file not found: {path}")
        return [], False
    try:
        xls = pd.ExcelFile(path)
    except Exception as e:  # locked, corrupt, etc.
        print(f"[FAIL] 5016 R4: cannot open {path.name}: {e}")
        return [], False

    frames: list[pd.DataFrame] = []
    for sheet, tag in R4_SHEETS.items():
        if sheet not in xls.sheet_names:
            print(f"[FAIL] 5016 R4: expected tab {sheet!r} not found "
                  f"(have {xls.sheet_names}).")
            return [], False

        df = pd.read_excel(xls, sheet_name=sheet, header=0, dtype=object)
        df.columns = [_norm(c) for c in df.columns]
        df = df[df["Bare Valve Code"].notna()]
        df = df[df["Bare Valve Code"].astype(str).str.strip().ne("")]
        df = df[df["Bare Valve Code"].astype(str).str.strip() != "Bare Valve Code"]

        # Every canonical column must be present verbatim EXCEPT the spec slots we
        # remap/blank via R4_SPEC_MAP. Refuse to guess if a base column is missing.
        needed = [c for c in CANON if c not in R4_SPEC_MAP]
        missing = [c for c in needed if c not in df.columns]
        if missing:
            print(f"[FAIL] 5016 R4 {tag}: missing canonical columns: {missing}")
            return [], False
        src_missing = [s for s in R4_SPEC_MAP.values() if s and s not in df.columns]
        if src_missing:
            print(f"[FAIL] 5016 R4 {tag}: spec-source columns absent: {src_missing}")
            return [], False

        out = pd.DataFrame()
        for c in CANON:
            if c in R4_SPEC_MAP:
                src = R4_SPEC_MAP[c]
                out[c] = df[src].values if src else ""
            else:
                out[c] = df[c].values
        out.insert(0, NAME_COL, f"{tag} CV ")
        frames.append(out)

        n = len(out)
        n_unique = out["Bare Valve Code"].astype(str).str.strip().nunique()
        dup_note = "" if n == n_unique else f"  ** {n - n_unique} DUPLICATE bare codes **"
        print(f"[ok]   {tag}: rows={n:6}  unique={n_unique:6}{dup_note}  "
              f"(R4_Updated {sheet!r} tab)")
        if base_codes is not None:
            new_codes = set(out["Bare Valve Code"].astype(str).str.strip())
            old_codes = {c for c in base_codes if c.startswith(tag)}
            added = sorted(new_codes - old_codes)
            removed = sorted(old_codes - new_codes)
            print(
                f"        vs V1: old={len(old_codes):6} new={len(new_codes):6} "
                f"added={len(added):4} removed={len(removed):4}"
            )
    print("        note: R4_Updated keeps Fail-Safe-Close MSD (renamed 'A Port "
          "Close / B Port Close'); Fail-Safe-Open MSD REMOVED by AVCON; "
          "Max Shut-off / Control Pressure blank for 5016.")
    return frames, True


def main() -> int:
    if not SRC_DIR.is_dir():
        print(f"[FAIL] source dir not found: {SRC_DIR}")
        return 2

    base = _baseline_v1()
    base_codes = (
        set(base["Bare Valve Code"].astype(str).str.strip()) if base is not None else None
    )
    if base_codes is None:
        print("[warn] V1 baseline unavailable — add/remove delta report skipped.\n")

    frames: list[pd.DataFrame] = []
    failed = False
    print("=== Per-series consolidation report ===")
    for fname, sheet, tag in SOURCES:
        path = SRC_DIR / fname
        df = pd.read_excel(path, sheet_name=sheet, header=0, dtype=object)
        df.columns = [_norm(c) for c in df.columns]
        df = df[df["Bare Valve Code"].notna()]
        df = df[df["Bare Valve Code"].astype(str).str.strip().ne("")]

        # Normalise the four named-spec slots (positions 43-46) to canonical
        # headers BY POSITION. Accept either the R2 real names or the legacy
        # "Additional Specification 1-4"; refuse to guess if the stable anchor
        # columns (43 ~ shut-off, 46 ~ control) aren't where we expect them.
        cols = list(df.columns)
        have_slots = len(cols) > SPEC_SLOTS[-1]
        a43 = cols[SPEC_ANCHOR_SHUTOFF].lower() if have_slots else ""
        a46 = cols[SPEC_ANCHOR_CONTROL].lower() if have_slots else ""
        legacy = a43.startswith("additional specification")
        anchored = "shut" in a43 and "control" in a46
        if not (legacy or anchored):
            failed = True
            got43 = cols[SPEC_ANCHOR_SHUTOFF] if have_slots else "<out of range>"
            got46 = cols[SPEC_ANCHOR_CONTROL] if have_slots else "<out of range>"
            print(
                f"[FAIL] {tag}: spec-slot anchors not found at positions "
                f"{SPEC_ANCHOR_SHUTOFF}/{SPEC_ANCHOR_CONTROL} (got {got43!r}/"
                f"{got46!r}) — refusing to guess."
            )
            continue
        for pos, name in zip(SPEC_SLOTS, SPEC_SLOT_NAMES):
            cols[pos] = name
        df.columns = cols

        missing = [c for c in CANON if c not in df.columns]
        extra = [c for c in df.columns if c not in CANON]
        if missing:
            failed = True
            print(f"[FAIL] {tag}: missing canonical columns: {missing}")
            continue

        out = df[CANON].copy()
        out.insert(0, NAME_COL, f"{tag} CV ")
        frames.append(out)

        n = len(out)
        n_unique = out["Bare Valve Code"].astype(str).str.strip().nunique()
        dup_note = "" if n == n_unique else f"  ** {n - n_unique} DUPLICATE bare codes **"
        line = f"[ok]   {tag}: rows={n:6}  unique={n_unique:6}{dup_note}  extra-dropped={extra or '[]'}"
        print(line)

        if base_codes is not None:
            new_codes = set(out["Bare Valve Code"].astype(str).str.strip())
            old_codes = {c for c in base_codes if c.startswith(tag)}
            added = sorted(new_codes - old_codes)
            removed = sorted(old_codes - new_codes)
            print(
                f"        vs V1: old={len(old_codes):6} new={len(new_codes):6} "
                f"added={len(added):4} removed={len(removed):4}"
            )
            if added:
                print(f"          + sample added : {added[:4]}{' …' if len(added) > 4 else ''}")
            if removed:
                print(f"          - sample removed: {removed[:4]}{' …' if len(removed) > 4 else ''}")

    # 5016A/5016B come from the R4 re-drop (working tab), not source_R2.
    r4_frames, r4_ok = _r4_5016_frames(base_codes)
    if not r4_ok:
        failed = True
    else:
        frames.extend(r4_frames)

    if failed:
        print("\n[ABORT] missing canonical columns — V2 NOT written.")
        return 1

    combined = pd.concat(frames, ignore_index=True)
    total = len(combined)
    total_unique = combined["Bare Valve Code"].astype(str).str.strip().nunique()

    print("\n=== Totals ===")
    print(f"  consolidated rows : {total}")
    print(f"  unique bare codes : {total_unique}")
    if total != total_unique:
        print(f"  ** WARNING: {total - total_unique} duplicate bare codes across series **")
    print(f"  columns           : {combined.shape[1]} (expect {len(CANON) + 1})")

    combined.to_excel(OUT, sheet_name=SHEET, index=False)
    print(f"\n[written] {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
