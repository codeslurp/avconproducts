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
and a consolidated sheet has one header row, this script normalises those four
slots to ONE canonical header set BY POSITION (see SPEC_SLOT_NAMES), guarded by
the stable anchor columns (43 ~ shut-off, 46 ~ control). These four columns are
now surfaced in the control-valve detail panel (catalog.py detail_columns 45-48).

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

# R2 named the first four "Additional Specification" slots (source positions
# 43-46, 0-based) with real but series-varying labels. The engine reads by
# position, so we collapse them to ONE canonical header set keyed by position.
# Order MUST match source positions 43,44,45,46. Surfaced in the detail panel
# via catalog.py CONTROL_VALVE.detail_columns (1-based cols 45-48).
SPEC_SLOTS = (43, 44, 45, 46)
SPEC_SLOT_NAMES = [
    "Max Shut-off Pressure",           # src 43 (was Additional Specification 1)
    "Fail Safe Close / A-Port Close",  # src 44 (was Additional Specification 2)
    "Fail Safe Open / B-Port Close",   # src 45 (was Additional Specification 3)
    "Control Pressure",                # src 46 (was Additional Specification 4)
]

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
    # positions 43-46: R2 named spec slots (normalised by position, see SPEC_SLOTS)
    "Max Shut-off Pressure", "Fail Safe Close / A-Port Close",
    "Fail Safe Open / B-Port Close", "Control Pressure",
    "Additional Specification 5", "Additional Specification 6",
    "Additional Specification 7", "Additional Specification 8",
    "Additional Specification 9", "Additional Specification 10",
    "Bare Valve Weight (kg)", "BOM Cost Rate (INR)",
    "Manufacturing Cost Rate (INR)", "Sale Cost Rate (INR)", "Offer Rate (INR)",
]

# (filename, sheet, series-tag) — the 6 control-valve series in the R2 drop.
SOURCES = [
    ("Control Valve Data for New Structure_5012A-B-R2.xlsx", "5012A CV ", "5012A"),
    ("Control Valve Data for New Structure_5012A-B-R2.xlsx", "5012B CV", "5012B"),
    ("Control Valve Data for New Structure 5016A-B_24.12.2025_R2.xlsx", "5016A CV ", "5016A"),
    ("Control Valve Data for New Structure 5016A-B_24.12.2025_R2.xlsx", "5016B CV", "5016B"),
    ("Control Valve Data for New Structure_5061A-01.01.26_R2.xlsx", "5061A CV ", "5061A"),
    ("Control Valve Data for New Structure 5066A 3W BELLOW SEAL_R2.xlsx", "5066A CV ", "5066A"),
]

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
        a43 = cols[SPEC_SLOTS[0]].lower() if len(cols) > SPEC_SLOTS[-1] else ""
        a46 = cols[SPEC_SLOTS[-1]].lower() if len(cols) > SPEC_SLOTS[-1] else ""
        legacy = a43.startswith("additional specification")
        anchored = "shut" in a43 and "control" in a46
        if not (legacy or anchored):
            failed = True
            print(
                f"[FAIL] {tag}: spec-slot anchors not found at positions "
                f"{SPEC_SLOTS[0]}/{SPEC_SLOTS[-1]} (got {cols[SPEC_SLOTS[0]]!r}/"
                f"{cols[SPEC_SLOTS[-1]]!r}) — refusing to guess."
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
