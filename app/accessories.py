"""Accessories loader.

Accessories are intentionally NOT a cascade-resolution catalog like valves and
actuators — the source file is a consolidated dashboard where 14 different
product families are stacked into one sheet, each with its OWN column schema
embedded as a header row. There's no single set of cascade dropdowns that
makes sense across all families, so the UI just browses the list with
checkboxes and lets the user pick any combination.

This module produces a flat list of `Accessory` dicts ready for the API to
serve. It filters out two flavors of garbage we know exist in the source:

  1. Header rows: each family's first row repeats the column headers
     (`code='Code'`, `model='Model'`). These appear as fake products if
     loaded blindly.
  2. Stray `Table_*` rows: 16 ball-valve rows leaked into the file. They
     have a family name like 'Table_2090F BV NEW CODEING' and no Code.

When/if engineering cleans up the source file, the filters here become
no-ops and can be removed — but they're cheap to keep and document.
"""
from __future__ import annotations

import shutil
import tempfile
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Any

import openpyxl


SHEET_NAME = "Accessories"
# Source column 1 holds the family marker (e.g. "ALR Data", "MOR", "BKT").
FAMILY_COL = 1
CODE_COL = 2


def _norm(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip().replace("\xa0", "")
        return s if s else None
    return v


def _clean_family(raw: str) -> str:
    """Normalize family names — strip the redundant ' Data' suffix some have
    (e.g. 'ALR Data' -> 'ALR', 'FCV Data' -> 'FCV'), keep others as-is."""
    s = str(raw).strip()
    if s.endswith(" Data"):
        s = s[: -len(" Data")]
    return s


def find_accessories_file(data_dir: Path) -> Path | None:
    """Pick the most recently modified .xlsx in data/Accessories/. Returns
    None if the folder doesn't exist or has no files — the app stays usable
    without accessories."""
    acc_dir = data_dir / "Accessories"
    if not acc_dir.exists():
        return None
    candidates = [
        p for p in acc_dir.rglob("*.xls*")
        if not p.name.startswith("~$")
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def load_accessories(data_dir: Path) -> dict[str, Any]:
    """Returns a dict with `rows`, `families`, `headers`, `source_file`.
    Rows are filtered (no header-row pollution, no Table_* garbage).
    `headers` is the row-1 column names from the source — used by the UI
    to label attribute values in the detail view."""
    src = find_accessories_file(data_dir)
    if src is None:
        return {"rows": [], "families": [], "headers": [], "source_file": None}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            wb = openpyxl.load_workbook(
                src, data_only=True, keep_vba=False, read_only=True
            )
        except PermissionError:
            # Source open in Excel; copy to temp and read that.
            tmp_dir = Path(tempfile.gettempdir()) / "valve-selector-cache"
            tmp_dir.mkdir(exist_ok=True)
            tmp_path = tmp_dir / src.name
            shutil.copyfile(src, tmp_path)
            wb = openpyxl.load_workbook(
                tmp_path, data_only=True, keep_vba=False, read_only=True
            )

    if SHEET_NAME not in wb.sheetnames:
        wb.close()
        print(
            f"[valve-selector] Accessories: no '{SHEET_NAME}' sheet in {src.name}; "
            f"skipping.",
            flush=True,
        )
        return {"rows": [], "families": [], "headers": [], "source_file": src.name}

    ws = wb[SHEET_NAME]
    raw_rows = list(ws.iter_rows(min_row=1, values_only=True))
    wb.close()

    if not raw_rows:
        return {"rows": [], "families": [], "headers": [], "source_file": src.name}

    headers = [str(_norm(h) or "").strip() for h in raw_rows[0]]
    # The header for col 1 in the source is itself a family tag ("ALR Data"),
    # not a real header — replace with "Family" so the UI can label it.
    if headers and headers[0]:
        headers[0] = "Family"

    rows: list[dict[str, Any]] = []
    families_seen: "OrderedDict[str, int]" = OrderedDict()
    skipped_header = 0
    skipped_table = 0
    skipped_no_code = 0

    for raw in raw_rows[1:]:
        if not raw or all(v is None for v in raw):
            continue
        family_raw = _norm(raw[FAMILY_COL - 1])
        code_raw = _norm(raw[CODE_COL - 1])

        # FILTER 1: stray Table_* leak from another catalog
        if family_raw and str(family_raw).startswith("Table_"):
            skipped_table += 1
            continue
        # FILTER 2: a family's own embedded header row (e.g. row with code='Code')
        if str(code_raw or "").strip().lower() == "code":
            skipped_header += 1
            continue
        # FILTER 3: rows with no code aren't useful for selection
        if not code_raw:
            skipped_no_code += 1
            continue

        family = _clean_family(family_raw) if family_raw else "Other"
        # Build attributes dict — pair headers with values, drop empty cells.
        attrs = []
        for i, val in enumerate(raw):
            v = _norm(val)
            if i == FAMILY_COL - 1 or i == CODE_COL - 1:
                continue  # family + code are top-level fields
            if v is None or v == "":
                continue
            label = headers[i] if i < len(headers) else f"Col {i + 1}"
            attrs.append({"label": label, "value": str(v)})

        rows.append({
            "code": str(code_raw).strip(),
            "family": family,
            "attrs": attrs,
        })
        families_seen[family] = families_seen.get(family, 0) + 1

    print(
        f"[valve-selector] Accessories: loaded {len(rows)} rows across "
        f"{len(families_seen)} families from {src.name} "
        f"(skipped: {skipped_header} headers, {skipped_table} Table_* "
        f"leaks, {skipped_no_code} no-code rows).",
        flush=True,
    )

    families = [{"name": name, "count": count} for name, count in families_seen.items()]
    return {
        "rows": rows,
        "families": families,
        "headers": headers,
        "source_file": src.name,
    }
