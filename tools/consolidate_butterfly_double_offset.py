#!/usr/bin/env python
"""Consolidate the Butterfly Valve *Double Offset* drop into a single dashboard
with per-SKU actuator recommendations baked in, so the positional loader in
`app/catalog.py` reads it via a plain `ValveTypeConfig` — NO engine change.

The drop (`Butterfly valve Double Offset Data.xlsx`) has:
  • main sheet "Butterfly Valve Double Offset D" — 1,764 SKUs across 3 series
    (4026B Wafer / 4027B Lug / 4028B Flanged), Pharma-style layout (leading
    Power-Query "Name" column, so Bare Valve Code is col 2).
  • "Double Acting" + "Single Acting" sheets — actuator SELECTION CHARTS keyed
    by valve *size* (not per SKU): each size maps to an actuator model at three
    air pressures (3.5 / 4 / 5.5 bar); Single Acting splits Fail-Close vs
    Fail-Open.

Unlike the Centric butterfly (per-SKU actuator columns in per-series files),
double-offset actuators are size-based charts. This tool joins each SKU's valve
size to the charts and bakes 9 models per SKU into new columns 60-68:
  60-62  Double Acting             @ 3.5 / 4 / 5.5 bar
  63-65  Single Acting Fail-Close  @ 3.5 / 4 / 5.5 bar
  66-68  Single Acting Fail-Open   @ 3.5 / 4 / 5.5 bar
Models are ACT-* (Rack & Pinion) or SYA-* (Scotch Yoke); the config routes each
by prefix. No electric chart exists for double-offset, so no electric columns.

Size-token trap: the Double-Acting chart writes 2½" as "2½\"" while Single-Acting
writes "2.5\"" and the main sheet uses "2½\"". `_norm_size` folds all of these to
one token so the join can't silently miss a size.

Strict: FAILS (non-zero exit, no file written) if the main sheet or a chart
header/size column can't be located, or if a main-sheet size (other than the
known-uncovered 18") has no chart row. Prints a coverage report.

Run:  py tools/consolidate_butterfly_double_offset.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

BFV_DIR = (
    Path(__file__).resolve().parent.parent
    / "data" / "Valve" / "Pune" / "Butterfly Valve Data Set"
)
SRC = BFV_DIR / "Butterfly valve Double Offset Data.xlsx"
OUT = BFV_DIR / "Butterfly Double Offset Dashboard.xlsx"

MAIN_SHEET_MARK = "Double Offset"          # substring of "Butterfly Valve Double Offset D"
SIZE_COL_NAME = "Data.Valve Size Inch (mm)"
KEY_COL_NAME = "Data.Bare Valve Code"
OUT_SHEET = "Butterfly Double Offset"       # loader sheet_marker matches this

# Sizes present in the SKU data but NOT in the actuator charts. 18" is a real
# gap in AVCON's selection chart (it jumps 16" -> 20"); those SKUs get no
# actuator recommendation. Listed here so the strict size-coverage check treats
# it as expected rather than aborting. Remove entries as charts gain the sizes.
UNCOVERED_SIZES = {"18"}

# Chart layout (0-based). Both charts put the inch size in col 3.
DA = dict(sheet="Double Acting", header_row=1, size_col=3, model_cols=(6, 7, 8))
SA = dict(sheet="Single Acting", header_row=3, size_col=3,
          fc_cols=(6, 7, 8), fo_cols=(9, 10, 11))

# New actuator columns appended after the main sheet's 59 columns.
ACT_COL_HEADERS = [
    "DA Actuator @3.5bar", "DA Actuator @4bar", "DA Actuator @5.5bar",
    "SR Fail-Close @3.5bar", "SR Fail-Close @4bar", "SR Fail-Close @5.5bar",
    "SR Fail-Open @3.5bar", "SR Fail-Open @4bar", "SR Fail-Open @5.5bar",
]


def _norm(s) -> str:
    return "" if s is None or (isinstance(s, float) and pd.isna(s)) else str(s).strip()


def _norm_size(s) -> str:
    """Fold every half-inch spelling to one token: 2½" / 2.5" / 2<mojibake>" -> '2.5'."""
    t = _norm(s).replace('"', "").strip()
    t = t.replace("½", ".5")
    # a leading integer followed only by non-digits (a stray fraction glyph) => .5
    t = re.sub(r"^(\d+)\D+$", r"\1.5", t)
    return t.strip()


def _sheet(xl: pd.ExcelFile, marker: str) -> str:
    for s in xl.sheet_names:
        if marker in s:
            return s
    raise SystemExit(f"[FAIL] no sheet matching {marker!r} in {SRC.name}")


def _build_size_lookup(xl: pd.ExcelFile) -> tuple[dict, dict, dict]:
    """Return (da, fc, fo) dicts: normalized-size -> (model@3.5, @4, @5.5)."""
    da_raw = pd.read_excel(xl, sheet_name=DA["sheet"], header=None, dtype=object)
    sa_raw = pd.read_excel(xl, sheet_name=SA["sheet"], header=None, dtype=object)

    def collect(raw, size_col, cols, first_data_row):
        out: dict[str, tuple] = {}
        for r in range(first_data_row, len(raw)):
            key = _norm_size(raw.iat[r, size_col]) if size_col < raw.shape[1] else ""
            # data rows have a numeric-ish size token; skip footer/blank rows
            if not re.match(r"^\d+(\.\d+)?$", key):
                continue
            models = tuple(_norm(raw.iat[r, c]) if c < raw.shape[1] else "" for c in cols)
            out[key] = models
        return out

    da = collect(da_raw, DA["size_col"], DA["model_cols"], DA["header_row"] + 1)
    fc = collect(sa_raw, SA["size_col"], SA["fc_cols"], SA["header_row"] + 1)
    fo = collect(sa_raw, SA["size_col"], SA["fo_cols"], SA["header_row"] + 1)
    for name, d in (("Double Acting", da), ("Fail-Close", fc), ("Fail-Open", fo)):
        if not d:
            raise SystemExit(f"[FAIL] {name} chart parsed to zero size rows — check layout.")
    return da, fc, fo


def main() -> int:
    if not SRC.is_file():
        print(f"[FAIL] source not found: {SRC}")
        return 2

    xl = pd.ExcelFile(SRC)
    main_sheet = _sheet(xl, MAIN_SHEET_MARK)
    df = pd.read_excel(xl, sheet_name=main_sheet, header=0, dtype=object)
    df.columns = [_norm(c) for c in df.columns]
    if KEY_COL_NAME not in df.columns or SIZE_COL_NAME not in df.columns:
        print(f"[FAIL] main sheet missing {KEY_COL_NAME!r}/{SIZE_COL_NAME!r}.")
        return 1

    # keep real SKU rows (drop blanks + any embedded repeated header row)
    df = df[df[KEY_COL_NAME].notna()]
    df = df[df[KEY_COL_NAME].astype(str).str.strip().ne("")]
    df = df[df[KEY_COL_NAME].astype(str).str.strip() != KEY_COL_NAME]

    da, fc, fo = _build_size_lookup(xl)

    # coverage check
    sku_sizes = {_norm_size(s) for s in df[SIZE_COL_NAME].dropna()}
    covered = set(da) & set(fc) & set(fo)
    gaps = sorted(sku_sizes - covered - UNCOVERED_SIZES)
    if gaps:
        print(f"[FAIL] SKU sizes with no actuator chart row (unexpected): {gaps}")
        return 1

    # bake 9 models per row
    blank9 = ("",) * 9
    baked = []
    n_no_rec = 0
    for _, row in df.iterrows():
        sz = _norm_size(row[SIZE_COL_NAME])
        if sz in covered:
            models = da[sz] + fc[sz] + fo[sz]
        else:
            models = blank9
            n_no_rec += 1
        baked.append(models)

    for i, hdr in enumerate(ACT_COL_HEADERS):
        df[hdr] = [b[i] for b in baked]

    # report
    print("=== Butterfly Double Offset consolidation ===")
    print(f"  main sheet         : {main_sheet!r}")
    print(f"  SKU rows           : {len(df)}")
    by_series = df[KEY_COL_NAME].astype(str).str[:5].value_counts().sort_index()
    for s, n in by_series.items():
        print(f"    {s}: {n}")
    print(f"  actuator sizes     : DA={len(da)} FC={len(fc)} FO={len(fo)}")
    print(f"  SKUs w/o actuator  : {n_no_rec} (sizes {sorted(UNCOVERED_SIZES)})")
    dup = df[KEY_COL_NAME].astype(str).str.strip().duplicated().sum()
    if dup:
        print(f"  ** WARNING: {dup} duplicate bare codes **")
    print(f"  output columns     : {df.shape[1]} (59 source + {len(ACT_COL_HEADERS)} actuator)")

    df.to_excel(OUT, sheet_name=OUT_SHEET, index=False)
    print(f"\n[written] {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
