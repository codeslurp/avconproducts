"""In-memory product catalogs (valves and actuators).

A `ValveTypeConfig` describes one product family — its cascade order, detail
columns, which file to read, and which sheets in that file are catalogs.

`load_all` reads every registered type at startup; types whose source file
isn't present in `data/` are skipped silently so the app still launches with
a subset.
"""
from __future__ import annotations

import shutil
import tempfile
import warnings
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl


@dataclass(frozen=True)
class PairedActuator:
    """One catalog-recommended actuator for a valve resolution.

    A valve row may name several recommended actuators in different columns
    (e.g. col 49 = pneumatic model, col 100 = electric rotary model).
    Each gets its own card in the result UI, pointing into the target
    catalog's picker with `target_field` pre-set to `model`.

    Use `target_type` for a single-catalog routing (e.g. all electric
    recommendations go to `electrical_rotary`).

    Use `target_type_by_prefix` when one recommendation column can name
    actuators from MULTIPLE catalogs and the right catalog is determined by a
    prefix on the model name. For example, butterfly valves' pneumatic column
    mixes `ACT-*` (Rack & Pinion) and `SYA-*` (Scotch Yoke); we route based
    on which prefix the recommended model starts with. The tuples are checked
    in order; first matching prefix wins. If no prefix matches, `target_type`
    in the API response is `None` and the front-end should show the model as
    informational text without a "jump to catalog" button.
    """
    model_col: int               # 1-based col on the valve row that names the model
    target_field: str            # cascade key in target to pre-fill (e.g. "model")
    label: str                   # heading shown above the card
    target_type: str | None = None
    target_type_by_prefix: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if bool(self.target_type) == bool(self.target_type_by_prefix):
            raise ValueError(
                f"PairedActuator must set exactly one of `target_type` or "
                f"`target_type_by_prefix` (got target_type={self.target_type!r}, "
                f"target_type_by_prefix={self.target_type_by_prefix!r})."
            )

    def resolve_target_type(self, model: str) -> str | None:
        """Pick the target catalog key for a recommended `model` name."""
        if self.target_type_by_prefix:
            for prefix, tt in self.target_type_by_prefix:
                if model.startswith(prefix):
                    return tt
            return None
        return self.target_type


@dataclass(frozen=True)
class EnrichmentSource:
    """VLOOKUP-style join: pulls columns from another workbook into the master
    catalog, keyed by a shared column (e.g. Bare Valve Code).

    Used by the master Ball Valve catalog to fold in the "Electric Actuator"
    columns that live only in the 4 per-series .xlsx extracts (2030F / 2060F /
    2070F / 2090F BV NEW CODEING)."""
    file_substring: str
    sheet_marker: str
    source_key_col: int                          # 1-based col in source = join key
    master_key_col: int                          # 1-based col in master = join key
    columns: tuple[tuple[int, int], ...]         # (source_col, master_dest_col) pairs


@dataclass(frozen=True)
class ExtraRowSource:
    """Adds ROWS (not columns) from a secondary workbook whose SKU keys aren't
    already in the catalog. Source columns are remapped to the catalog's column
    positions via `column_map`. Used to fold in SKUs that live only in a
    secondary file with a different layout (e.g. the 162 Pharma SKUs that exist
    only in 'Pharma Dashboard.xlsx', or actuators present only in a combined
    workbook). Non-destructive: nothing is written back to any source file.

    Dedup: a source row is added only if its key isn't already in the catalog,
    so re-listing existing SKUs is harmless. `key_pattern` (optional regex) gates
    which source rows count — used to skip embedded header/garbage rows."""
    file_substring: str
    sheet_marker: str
    key_col: int                                 # 1-based source col holding the SKU key
    master_key_col: int                          # 1-based catalog col the key maps to
    column_map: tuple[tuple[int, int], ...]      # (source_col, master_col) pairs
    path_contains: str | None = None
    key_pattern: str | None = None               # only add rows whose key matches


@dataclass(frozen=True)
class ValveTypeConfig:
    key: str                            # URL/JSON identifier, e.g. "ball"
    label: str                          # Section title shown in the UI
    category: str                       # Top-level picker (e.g. "Valves", "Actuators").
                                        # Each distinct category gets its own picker widget.
    file_substring: str                 # substring used to pick the file from data/
    sheet_marker: str                   # substring marking which sheets are catalogs
    cascade: list[tuple[str, int, str]] # ordered (form-key, 1-based col, label)
    detail_columns: list[tuple[int, str]]  # (1-based col, display label)

    # Sub-grouping shown as a heading inside the picker menu (None = no heading).
    # E.g. within Actuators picker: "Pneumatic" vs "Electrical".
    subgroup: str | None = None

    # Optional path scope to disambiguate same-named files across subfolders.
    # find_catalog_file matches on FILENAME only, so when two folders hold a
    # file with the same name (e.g. Pune and Mumbai both ship a
    # "Valve_Code_Selector_Dashboard.xlsx"), set this to a path fragment that
    # only the intended file's path contains (e.g. "Mumbai"). None = no scoping.
    path_contains: str | None = None

    # Headline result cards. Defaults match valves. Actuators override these
    # because they have a Code + Model (not a separate Catalogue Code) and
    # no torque-vs-FOS calculation.
    primary_label: str = "Bare Valve Code"
    primary_col: int = 1
    secondary_label: str | None = "Catalogue Code"
    secondary_col: int | None = 2
    show_bto_fos: bool = True
    bto_col: int = 39                   # only used if show_bto_fos

    # Optional pairings: each entry in the tuple becomes its own
    # "Catalog-recommended actuator" card in the result panel, with a button
    # that jumps into that catalog's picker. Ball valves declare TWO: a
    # pneumatic R&P model (col 49) and an electric rotary model (col 100,
    # enriched in from the per-series files).
    paired_actuators: tuple[PairedActuator, ...] = ()

    # Optional VLOOKUP-style enrichment sources merged in after the main load.
    enrichment_sources: tuple[EnrichmentSource, ...] = ()

    # Optional secondary files that ADD rows (SKUs missing from the main file).
    extra_row_sources: tuple[ExtraRowSource, ...] = ()


BALL_VALVE = ValveTypeConfig(
    key="ball",
    label="Ball Valve",
    category="Valves",
    subgroup="Pune",
    file_substring="Ball Valve",
    sheet_marker="BV NEW CODEING",
    # Recommended actuators per SKU. As of 2026-05-27, the richer source is
    # the dashboard file's "Ball Valve Actuator combination" sheet — it carries
    # pressure-specific labels (3.5/4/5.5 bar) for the 9 pneumatic positions
    # AND the 2 electric positions. The enrichment below pulls source cols
    # 49-59 into master cols 100-110, and these entries read the enriched cols.
    # Dedup is by (target_type, model), so if the same model is valid at
    # multiple pressures (common: ACT-050D works at 3.5, 4, AND 5.5 bar), the
    # user sees one chip with the first matching label.
    paired_actuators=(
        # Pneumatic Double Acting — 3 pressure variants
        PairedActuator(model_col=100, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Double Acting @ 3.5 bar"),
        PairedActuator(model_col=101, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Double Acting @ 4 bar"),
        PairedActuator(model_col=102, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Double Acting @ 5.5 bar"),
        # Pneumatic Spring Return Fail-Close — 3 pressure variants
        PairedActuator(model_col=103, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Close @ 3.5 bar"),
        PairedActuator(model_col=104, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Close @ 4 bar"),
        PairedActuator(model_col=105, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Close @ 5.5 bar"),
        # Pneumatic Spring Return Fail-Open — 3 pressure variants
        PairedActuator(model_col=106, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Open @ 3.5 bar"),
        PairedActuator(model_col=107, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Open @ 4 bar"),
        PairedActuator(model_col=108, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Open @ 5.5 bar"),
        # Electric — no sub-text on chips (user's choice which to pick).
        # Plain "Electric" labels are stripped to empty by the JS prefix
        # regex, so each chip shows just the model code with no sub-line.
        PairedActuator(model_col=109, target_type="electrical_rotary", target_field="model",
                       label="Electric"),
        PairedActuator(model_col=110, target_type="electrical_rotary", target_field="model",
                       label="Electric"),
        # Per-series files (cols 49-59 -> 111-121): the COMPLETE alternative
        # actuator set. The dashboard's fixed 3.5/4/5.5-bar slots above drop some
        # valid 3rd-alternative models (verified: 10 models across 140 SKUs, e.g.
        # ACT-063SR07). Dedup by (target_type, model) at resolve time means these
        # only ADD chips for models not already surfaced above — no duplicates.
        PairedActuator(model_col=111, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Double Acting"),
        PairedActuator(model_col=112, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Double Acting"),
        PairedActuator(model_col=113, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Double Acting"),
        PairedActuator(model_col=114, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Close"),
        PairedActuator(model_col=115, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Close"),
        PairedActuator(model_col=116, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Close"),
        PairedActuator(model_col=117, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Open"),
        PairedActuator(model_col=118, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Open"),
        PairedActuator(model_col=119, target_type="pneumatic_rp", target_field="model",
                       label="Pneumatic — Spring Return Fail-Open"),
        PairedActuator(model_col=120, target_type="electrical_rotary", target_field="model",
                       label="Electric"),
        PairedActuator(model_col=121, target_type="electrical_rotary", target_field="model",
                       label="Electric"),
    ),
    cascade=[
        ("series",          4,  "Series"),
        ("size",            5,  "Valve Size"),
        ("body_material",   6,  "Body Material"),
        ("ball_material",   7,  "Ball Material"),
        ("seat_material",   8,  "Seat Material"),
        ("characteristics", 9,  "Characteristics"),
        ("end_connection", 10,  "End Connections"),
        ("ball_type",      22,  "Ball Type"),
    ],
    detail_columns=[
        (1, "Bare Valve Code"), (2, "Catalogue Code"), (3, "Make"),
        (11, "Valve Type"), (12, "Design Standard"), (13, "Face to Face"),
        (14, "Port Size"), (15, "No. of Ports"), (16, "Valve Kv (m³/hr)"),
        (17, "Body Style"), (18, "Flow Direction"), (19, "End Piece Material"),
        (20, "Type of Bonnet"), (21, "Stem Material"),
        (23, "Gland Packing"), (24, "Body Packing"),
        (25, "Flange Dimensions"), (26, "Flange Drilling"),
        (27, "Pressure Rating"), (28, "Operating Temp Range (°C)"),
        (29, "Hardware"), (30, "Valve Paint"),
        (31, "Testing Standard"), (32, "Leakage Class"),
        (33, "Body Test Pressure (barg)"), (34, "Body Test Media"),
        (35, "Seat Leakage Test Pressure (barg)"), (36, "Seat Leakage Test Media"),
        (37, "Product Group"), (38, "Certification"),
        (39, "BTO"), (40, "ETO"), (41, "BTC"), (42, "ETC"), (43, "Run"),
        (44, "Top PCD"), (45, "Stem Shape"), (46, "Stem Dimension"),
        (47, "Stem Orientation"), (48, "Stem Protrusion (mm)"),
        (49, "Double Acting Actuator 1"), (50, "Double Acting Actuator 2"),
        (51, "Double Acting Actuator 3"),
        (52, "Single Acting Fail-Safe Close 1"),
        (53, "Single Acting Fail-Safe Close 2"),
        (54, "Single Acting Fail-Safe Close 3"),
        (55, "Single Acting Fail-Safe Open 1"),
        (56, "Single Acting Fail-Safe Open 2"),
        (57, "Single Acting Fail-Safe Open 3"),
        # Enriched-in cols using descriptive labels from the dashboard file's
        # "Ball Valve Actuator combination" sheet (3.5 / 4 / 5.5 bar variants).
        (100, "Double Acting Actuator @ 3.5 bar"),
        (101, "Double Acting Actuator @ 4 bar"),
        (102, "Double Acting Actuator @ 5.5 bar"),
        (103, "Single Acting Fail-Safe Close @ 3.5 bar"),
        (104, "Single Acting Fail-Safe Close @ 4 bar"),
        (105, "Single Acting Fail-Safe Close @ 5.5 bar"),
        (106, "Single Acting Fail-Safe Open @ 3.5 bar"),
        (107, "Single Acting Fail-Safe Open @ 4 bar"),
        (108, "Single Acting Fail-Safe Open @ 5.5 bar"),
        (109, "Electric Actuator 1"), (110, "Electric Actuator 2"),
        # Per-series files (cols 49-59 -> 111-121): the complete alternative
        # actuator set, surfacing models the dashboard's pressure slots omit.
        (111, "Double Acting Actuator (alt 1)"), (112, "Double Acting Actuator (alt 2)"),
        (113, "Double Acting Actuator (alt 3)"),
        (114, "Single Acting Fail-Safe Close (alt 1)"),
        (115, "Single Acting Fail-Safe Close (alt 2)"),
        (116, "Single Acting Fail-Safe Close (alt 3)"),
        (117, "Single Acting Fail-Safe Open (alt 1)"),
        (118, "Single Acting Fail-Safe Open (alt 2)"),
        (119, "Single Acting Fail-Safe Open (alt 3)"),
        (120, "Electric Actuator (alt 1)"), (121, "Electric Actuator (alt 2)"),
    ],
    # Enrichment sources, merged in after the main load:
    #  1. The dashboard's "Ball Valve Actuator combination" sheet -> cols 100-110
    #     (9 pneumatic at 3.5/4/5.5 bar + 2 electric), pressure-labelled.
    #  2. The 4 per-series files -> NEW cols 111-121 (clear of 100-110). These
    #     carry the COMPLETE alternative actuator set; the union (deduped at
    #     resolve time) recovers models the dashboard's fixed pressure slots drop
    #     (verified: 10 models across 140 SKUs).
    enrichment_sources=(
        EnrichmentSource(
            file_substring="Valve_Code_Selector_Dashboard",
            sheet_marker="Ball Valve Actuator combination",
            source_key_col=1, master_key_col=1,
            columns=(
                (49, 100), (50, 101), (51, 102),
                (52, 103), (53, 104), (54, 105),
                (55, 106), (56, 107), (57, 108),
                (58, 109), (59, 110),
            ),
        ),
        EnrichmentSource(
            file_substring="2030F BV NEW CODEING", sheet_marker="2030F BV NEW CODEING",
            source_key_col=1, master_key_col=1,
            columns=((49,111),(50,112),(51,113),(52,114),(53,115),(54,116),(55,117),(56,118),(57,119),(58,120),(59,121)),
        ),
        EnrichmentSource(
            file_substring="2060F BV NEW CODEING", sheet_marker="2060F BV NEW CODEING",
            source_key_col=1, master_key_col=1,
            columns=((49,111),(50,112),(51,113),(52,114),(53,115),(54,116),(55,117),(56,118),(57,119),(58,120),(59,121)),
        ),
        EnrichmentSource(
            file_substring="2070F BV NEW CODEING", sheet_marker="2070F BV NEW CODEING",
            source_key_col=1, master_key_col=1,
            columns=((49,111),(50,112),(51,113),(52,114),(53,115),(54,116),(55,117),(56,118),(57,119),(58,120),(59,121)),
        ),
        EnrichmentSource(
            file_substring="2090F BV NEW CODEING", sheet_marker="2090F BV NEW CODEING",
            source_key_col=1, master_key_col=1,
            columns=((49,111),(50,112),(51,113),(52,114),(53,115),(54,116),(55,117),(56,118),(57,119),(58,120),(59,121)),
        ),
    ),
)


BUTTERFLY_VALVE = ValveTypeConfig(
    key="butterfly",
    label="Butterfly Valve (Centric)",
    category="Valves",
    subgroup="Pune",
    file_substring="Butterfly Valve",
    sheet_marker="BFV NEW CODEING",
    # NOTE: catalog has a "Disc Type" column (V/22) but it is empty in all
    # 43,200 rows, so it's omitted from the cascade — adding it would dead-end
    # every selection. Re-add if/when the catalog starts populating that column.
    # Unlike ball valves, the butterfly MASTER file has "Additional Specification"
    # data at cols 49-53 (NOT actuator data). The actuator pairings live only in
    # the per-series files (cols 49-59), so we enrich them into NEW master cols
    # 100-110 to avoid clobbering the master's existing data.
    # Coverage caveat: only 3 of 6 master sheets (4020B/4022B/4023B) have matching
    # per-series files today — 4020M/4022M/4023M "BON" variants will get NO
    # actuator recommendation until per-series files are produced for them.
    paired_actuators=(
        # Per-series files populate up to 11 actuator positions per SKU
        # (cols 100-110 after enrichment). Surface all of them; dedup happens
        # at resolve time so identical models across positions collapse to one
        # card. Movement-type labels distinguish Double Acting from Spring
        # Return Fail-Close from Spring Return Fail-Open.
        # Pneumatic — mixed routing: ACT-* → R&P, SYA-* → Scotch Yoke.
        # Bare prefixes (no trailing dash) catch no-dash format-drift in source.
        PairedActuator(
            model_col=100, target_field="model",
            label="Pneumatic — Double Acting",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        PairedActuator(
            model_col=101, target_field="model",
            label="Pneumatic — Double Acting (alt 1)",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        PairedActuator(
            model_col=102, target_field="model",
            label="Pneumatic — Double Acting (alt 2)",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        PairedActuator(
            model_col=103, target_field="model",
            label="Pneumatic — Spring Return Fail-Close",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        PairedActuator(
            model_col=104, target_field="model",
            label="Pneumatic — Spring Return Fail-Close (alt 1)",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        PairedActuator(
            model_col=105, target_field="model",
            label="Pneumatic — Spring Return Fail-Close (alt 2)",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        PairedActuator(
            model_col=106, target_field="model",
            label="Pneumatic — Spring Return Fail-Open",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        PairedActuator(
            model_col=107, target_field="model",
            label="Pneumatic — Spring Return Fail-Open (alt 1)",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        PairedActuator(
            model_col=108, target_field="model",
            label="Pneumatic — Spring Return Fail-Open (alt 2)",
            target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy")),
        ),
        # Electric — single-target (all values are EA-* or QM-*, both in
        # electrical_rotary catalog). Plain "Electric" label so each chip
        # shows only the model code (no sub-text — user picks freely).
        PairedActuator(
            model_col=109, target_type="electrical_rotary", target_field="model",
            label="Electric",
        ),
        PairedActuator(
            model_col=110, target_type="electrical_rotary", target_field="model",
            label="Electric",
        ),
    ),
    cascade=[
        ("series",          4,  "Series"),
        ("size",            5,  "Valve Size"),
        ("body_material",   6,  "Body Material"),
        ("disc_material",   7,  "Disc Material"),
        ("seat_material",   8,  "Seat Material"),
        ("characteristics", 9,  "Characteristics"),
        ("end_connection", 10,  "End Connections"),
    ],
    detail_columns=[
        (1, "Bare Valve Code"), (2, "Catalogue Code"), (3, "Make"),
        (11, "Valve Type"), (12, "Design Standard"), (13, "Face to Face"),
        (14, "Port Size"), (15, "No. of Ports"), (16, "Valve Kv (m³/hr)"),
        (17, "Body Style"), (18, "Flow Direction"), (19, "Bonnet Material"),
        (20, "Type of Bonnet"), (21, "Stem Material"),
        (23, "Gland Packing"), (24, "Body Packing"),
        (25, "Flange Dimensions"), (26, "Flange Drilling"),
        (27, "Pressure Rating"), (28, "Operating Temp Range (°C)"),
        (29, "Hardware"), (30, "Valve Paint"),
        (31, "Testing Standard"), (32, "Leakage Class"),
        (33, "Body Test Pressure (barg)"), (34, "Body Test Media"),
        (35, "Seat Leakage Test Pressure (barg)"), (36, "Seat Leakage Test Media"),
        (37, "Product Group"), (38, "Certification"),
        (39, "BTO"), (40, "ETO"), (41, "BTC"), (42, "ETC"), (43, "Run"),
        (44, "Top PCD"), (45, "Stem Shape"), (46, "Stem Dimension"),
        (47, "Stem Orientation"), (48, "Stem Protrusion (mm)"),
        (49, "Additional Specification 1"), (50, "Additional Specification 2"),
        (51, "Additional Specification 3"), (52, "Additional Specification 4"),
        (53, "Additional Specification 5"), (54, "Bare Valve Weight (kg)"),
        # Merged from the 3 per-series .xlsx files via Bare Valve Code lookup.
        # Stored at c100+ to keep clear of master columns.
        (100, "Double Acting Actuator 1"), (101, "Double Acting Actuator 2"),
        (102, "Double Acting Actuator 3"),
        (103, "Single Acting Fail-Safe Close 1"),
        (104, "Single Acting Fail-Safe Close 2"),
        (105, "Single Acting Fail-Safe Close 3"),
        (106, "Single Acting Fail-Safe Open 1"),
        (107, "Single Acting Fail-Safe Open 2"),
        (108, "Single Acting Fail-Safe Open 3"),
        (109, "Electric Actuator 1"), (110, "Electric Actuator 2"),
    ],
    # Each per-series file maps its actuator cols 49-59 into master cols 100-110.
    enrichment_sources=(
        EnrichmentSource(
            file_substring="4020B BFV NEW CODEING",
            sheet_marker="4020B BFV NEW CODEING",
            source_key_col=1, master_key_col=1,
            columns=(
                (49, 100), (50, 101), (51, 102),
                (52, 103), (53, 104), (54, 105),
                (55, 106), (56, 107), (57, 108),
                (58, 109), (59, 110),
            ),
        ),
        EnrichmentSource(
            file_substring="4022B BFV NEW CODEING",
            sheet_marker="4022B BFV NEW CODEING",
            source_key_col=1, master_key_col=1,
            columns=(
                (49, 100), (50, 101), (51, 102),
                (52, 103), (53, 104), (54, 105),
                (55, 106), (56, 107), (57, 108),
                (58, 109), (59, 110),
            ),
        ),
        EnrichmentSource(
            file_substring="4023B BFV NEW CODEING",
            sheet_marker="4023B BFV NEW CODEING",
            source_key_col=1, master_key_col=1,
            columns=(
                (49, 100), (50, 101), (51, 102),
                (52, 103), (53, 104), (54, 105),
                (55, 106), (56, 107), (57, 108),
                (58, 109), (59, 110),
            ),
        ),
    ),
)


PHARMA_VALVE = ValveTypeConfig(
    key="pharma",
    label="Pharma Valve",
    category="Valves",
    subgroup="Mumbai",
    # The catalog lives in the 'Pharma' sheet of a Valve_Code_Selector_Dashboard
    # .xlsx whose NAME collides with the Pune ball-valve dashboard, so we scope
    # the file search to the Mumbai subfolder.
    file_substring="Valve_Code_Selector_Dashboard",
    path_contains="Mumbai",
    sheet_marker="Pharma",
    # Column layout is shifted +1 vs the Ball Valve master: this sheet has a
    # leading Power-Query "Name" column (c1, "Table_…"), so Bare Valve Code is
    # c2, Series c5, etc. The 728 spacer rows with an empty Bare Valve Code are
    # dropped by the primary-col row filter in Catalog._load.
    primary_label="Bare Valve Code", primary_col=2,
    secondary_label="Catalogue Code", secondary_col=3,
    show_bto_fos=True, bto_col=40,
    # Recommended actuators are present IN this sheet (c50–60), so no enrichment
    # is needed (unlike ball/butterfly). Pneumatic models are ACT-* (Rack &
    # Pinion); prefix routing also handles any SYA-* (Scotch Yoke). Electric
    # models (c59–60) route to the rotary catalog. Dedup by (target_type, model)
    # at resolve time collapses repeats across the three positions.
    paired_actuators=(
        PairedActuator(model_col=50, target_field="model",
                       label="Pneumatic — Double Acting",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        PairedActuator(model_col=51, target_field="model",
                       label="Pneumatic — Double Acting (alt 1)",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        PairedActuator(model_col=52, target_field="model",
                       label="Pneumatic — Double Acting (alt 2)",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        PairedActuator(model_col=53, target_field="model",
                       label="Pneumatic — Spring Return Fail-Close",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        PairedActuator(model_col=54, target_field="model",
                       label="Pneumatic — Spring Return Fail-Close (alt 1)",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        PairedActuator(model_col=55, target_field="model",
                       label="Pneumatic — Spring Return Fail-Close (alt 2)",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        PairedActuator(model_col=56, target_field="model",
                       label="Pneumatic — Spring Return Fail-Open",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        PairedActuator(model_col=57, target_field="model",
                       label="Pneumatic — Spring Return Fail-Open (alt 1)",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        PairedActuator(model_col=58, target_field="model",
                       label="Pneumatic — Spring Return Fail-Open (alt 2)",
                       target_type_by_prefix=(("ACT", "pneumatic_rp"), ("SYA", "pneumatic_sy"))),
        # Linear actuator (HA-*, 5-6 bar) — a pneumatic operation type surfaced in
        # the SAME recommendation list as Double Acting / Spring Return. As of the
        # HA Series datasheet (2026-06-03) this IS a browsable family
        # (PNEUMATIC_HA below), so the chip is now clickable: target_type
        # "pneumatic_ha" routes the HA-* model into that catalog. Data present only
        # on the Pharma Dashboard SKUs that carry a linear model (col 122 via
        # extra_row_sources); all referenced models (HA-85/110/125 /NC) exist in
        # the HA catalog.
        PairedActuator(model_col=122, target_type="pneumatic_ha", target_field="model",
                       label="Pneumatic — Linear (5-6 bar)"),
        PairedActuator(model_col=59, target_type="electrical_rotary", target_field="model",
                       label="Electric"),
        PairedActuator(model_col=60, target_type="electrical_rotary", target_field="model",
                       label="Electric"),
    ),
    # "Characteristics" (c10) is omitted from the cascade — it has a single value
    # ("ONF") across all rows, so a dropdown for it would be dead weight (same
    # reasoning the Electrical Rotary config uses). It still appears in details.
    cascade=[
        ("series",          5,  "Series"),
        ("size",            6,  "Valve Size"),
        ("body_material",   7,  "Body Material"),
        ("ball_material",   8,  "Ball Material"),
        ("seat_material",   9,  "Seat Material"),
        ("end_connection", 11,  "End Connections"),
        ("ball_type",      23,  "Ball Type"),
    ],
    detail_columns=[
        (2, "Bare Valve Code"), (3, "Catalogue Code"), (4, "Make"),
        (5, "Series"), (6, "Valve Size"),
        (7, "Body Material"), (8, "Ball Material"), (9, "Seat Material"),
        (10, "Characteristics"), (11, "End Connections"),
        (12, "Valve Type"), (13, "Design Standard"), (14, "Face to Face"),
        (15, "Port Size"), (16, "No. of Ports"), (17, "Valve Kv (m³/hr)"),
        (18, "Body Style"), (19, "Flow Direction"), (20, "End Piece Material"),
        (21, "Type of Bonnet"), (22, "Stem Material"), (23, "Ball Type"),
        (24, "Gland Packing"), (25, "Body Packing"),
        (26, "Flange Dimensions"), (27, "Flange Drilling"),
        (28, "Pressure Rating"), (29, "Operating Temp Range (°C)"),
        (30, "Hardware"), (31, "Valve Paint"),
        (32, "Testing Standard"), (33, "Leakage Class"),
        (34, "Body Test Pressure (barg)"), (35, "Body Test Media"),
        (36, "Seat Leakage Test Pressure (barg)"), (37, "Seat Leakage Test Media"),
        (38, "Product Group"), (39, "Certification"),
        (40, "BTO"), (41, "ETO"), (42, "BTC"), (43, "ETC"), (44, "Run"),
        (45, "Top PCD"), (46, "Stem Shape"), (47, "Stem Dimension"),
        (48, "Stem Orientation"), (49, "Stem Protrusion (mm)"),
        (50, "Double Acting Actuator 1"), (51, "Double Acting Actuator 2"),
        (52, "Double Acting Actuator 3"),
        (53, "Single Acting Fail-Safe Close 1"),
        (54, "Single Acting Fail-Safe Close 2"),
        (55, "Single Acting Fail-Safe Close 3"),
        (56, "Single Acting Fail-Safe Open 1"),
        (57, "Single Acting Fail-Safe Open 2"),
        (58, "Single Acting Fail-Safe Open 3"),
        (59, "Electric Actuator 1"), (60, "Electric Actuator 2"),
        # From the Pharma Dashboard extra-row source (no equivalent in the main
        # 'Pharma' sheet). Linear (122) ALSO surfaces as a 'Linear' chip in the
        # Recommended Actuator list (paired_actuators above) — it's a pneumatic
        # operation type, not just a spec; it stays here too so the full
        # attribute dump is complete. Manual (123) is detail-only.
        (122, "Linear Actuator (5-6 bar)"), (123, "Manual Operator"),
    ],
    extra_row_sources=(
        # Fold in the 162 Pharma SKUs that exist ONLY in Pharma Dashboard.xlsx
        # ('Ball Valve Data Sheet Structure' sheet, ball layout: c1=Bare Code, so
        # base cols map +1 into the 'Pharma' layout). Pneumatic/electric actuators
        # land in cols 50-60 (surfaced as chips by paired_actuators above);
        # Linear/Manual land in 122/123 (detail only). key_pattern skips the
        # sheet's embedded header rows.
        ExtraRowSource(
            file_substring="Pharma Dashboard",
            sheet_marker="Ball Valve Data Sheet Structure",
            path_contains="Mumbai",
            key_col=1, master_key_col=2,
            key_pattern=r"^[0-9]{3,4}[A-Z]",
            column_map=(
                (1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,9),(9,10),(10,11),
                (11,12),(12,13),(13,14),(14,15),(15,16),(16,17),(17,18),(18,19),
                (19,20),(20,21),(21,22),(22,23),(23,24),(24,25),(25,26),(26,27),
                (27,28),(28,29),(29,30),(30,31),(31,32),(32,33),(33,34),(34,35),
                (35,36),(36,37),(37,38),(38,39),(39,40),(40,41),(41,42),(42,43),
                (43,44),(44,45),(45,46),(46,47),(47,48),(48,49),
                (49,50),(50,51),(51,52),(52,53),(53,54),(54,55),(55,56),(56,57),(57,58),
                (59,59),(60,60),
                (58,122),(61,123),
            ),
        ),
    ),
)


# ---- Actuators --------------------------------------------------------------
# All three actuator catalogs share a similar layout:
#   col 1 = CODE          (the SKU)
#   col 5 = Model         (human-friendly identifier)
#   col 4 = Type          (DA / Spring Return / Rotary motorised / …)
#   per-type specs from col 6 onwards
# Headline cards are Code + Model. BTO/FOS doesn't apply.

PNEUMATIC_RACK_PINION = ValveTypeConfig(
    key="pneumatic_rp",
    label="Rack & Pinion",
    category="Actuators",
    subgroup="Pneumatic Rotary",
    file_substring="Rack & Pinion",
    sheet_marker="Rack & Pinion ACT",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # The 4 fields that uniquely determine a Code per AVCON's workflow.
    # Verified 2026-05-26: {Model + Body + Shaft Female + O-Ring} disambiguates
    # 1,618 of 1,619 combinations (99.9%); only ACT-075SR12+Aluminium+SQ.17+
    # Viton Low resolves to two codes (RPAS0716 / RPAS0724) which differ on
    # Temperature Rating only. Other attributes (Type, Springs, Pneumatic
    # Connections, Application, Certification) stay in detail_columns so they
    # still display in the resolved-actuator panel.
    cascade=[
        ("model",            5, "Model"),
        ("body_material",    8, "Body Material"),
        ("shaft_female",    21, "Shaft Female"),
        ("oring_material",   9, "O-Ring Material"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator"), (3, "Make"), (4, "Type"), (5, "Model"),
        (6, "No. of Springs"), (7, "Movement"),
        (8, "Body Material"), (9, "O-Ring Material"), (10, "Temperature Rating"),
        (11, "Min Pneumatic Supply"), (12, "Max Pneumatic Supply"),
        (13, "Pneumatic Connections"), (14, "Actuator Orientation"),
        (15, "Application"), (16, "Painting"), (17, "Certification"),
        (18, "Catalogue Code"), (21, "Shaft Female"), (22, "PCD"),
        (23, "Torque @ 2.5 bar (Break)"), (24, "Torque @ 2.5 bar (End)"),
        (25, "Torque @ 3 bar (Break)"),   (26, "Torque @ 3 bar (End)"),
        (27, "Torque @ 3.5 bar (Break)"), (28, "Torque @ 3.5 bar (End)"),
        (29, "Torque @ 4 bar (Break)"),   (30, "Torque @ 4 bar (End)"),
        (31, "Torque @ 4.5 bar (Break)"), (32, "Torque @ 4.5 bar (End)"),
        (33, "Torque @ 5 bar (Break)"),   (34, "Torque @ 5 bar (End)"),
        (35, "Torque @ 5.5 bar (Break)"), (36, "Torque @ 5.5 bar (End)"),
        (37, "Torque @ 6 bar (Break)"),   (38, "Torque @ 6 bar (End)"),
        (39, "Torque @ 7 bar (Break)"),   (40, "Torque @ 7 bar (End)"),
        (41, "Torque @ 8 bar (Break)"),   (42, "Torque @ 8 bar (End)"),
        (43, "Spring Break Torque"), (44, "Spring End Torque"),
    ],
)


PNEUMATIC_SCOTCH_YOKE = ValveTypeConfig(
    key="pneumatic_sy",
    label="Scotch Yoke",
    category="Actuators",
    subgroup="Pneumatic Rotary",
    file_substring="Scotch Yoke",
    sheet_marker="Scotch Yoke Actuator SYA",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # Same 4-field shape as R&P. Verified 2026-05-26: 479 of 480 combos
    # (99.8%) resolve to one Code; one duplicate (SYAS0604 / SYAS0606) shows
    # no difference in any declared column — likely a data-quality issue
    # worth flagging engineering.
    cascade=[
        ("model",            5, "Model"),
        ("body_material",    8, "Body Material"),
        ("shaft_female",    21, "Shaft Female"),
        ("oring_material",   9, "O-Ring Material"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator"), (3, "Make"), (4, "Type"), (5, "Model"),
        (6, "Spring Model"), (7, "Movement"),
        (8, "Body Material"), (9, "O-Ring Material"), (10, "Temperature Rating"),
        (11, "Min Pneumatic Supply"), (12, "Max Pneumatic Supply"),
        (13, "Pneumatic Connections"), (14, "Actuator Orientation"),
        (15, "Application"), (16, "Painting"), (17, "Certification"),
        (21, "Shaft Female"), (22, "PCD"),
        (23, "Torque @ 3 bar (Break)"),   (25, "Torque @ 3 bar (End)"),
        (26, "Torque @ 3.5 bar (Break)"), (28, "Torque @ 3.5 bar (End)"),
        (29, "Torque @ 4 bar (Break)"),   (31, "Torque @ 4 bar (End)"),
        (32, "Torque @ 4.5 bar (Break)"), (34, "Torque @ 4.5 bar (End)"),
        (35, "Torque @ 5 bar (Break)"),   (37, "Torque @ 5 bar (End)"),
        (38, "Torque @ 5.5 bar (Break)"), (40, "Torque @ 5.5 bar (End)"),
        (41, "Torque @ 6 bar (Break)"),   (43, "Torque @ 6 bar (End)"),
        (44, "Torque @ 7 bar (Break)"),   (46, "Torque @ 7 bar (End)"),
        (47, "Torque @ 8 bar (Break)"),   (49, "Torque @ 8 bar (End)"),
        (50, "Spring Break Torque"), (52, "Spring End Torque"),
    ],
)


ELECTRICAL_ROTARY = ValveTypeConfig(
    key="electrical_rotary",
    label="Rotary",
    category="Actuators",
    subgroup="Electrical",
    # Was "Electrical Actuator" — too broad: it also matched the newer
    # "Electrical Actuator Linear..." file, which (being newest) hijacked this
    # catalog. Anchored to "Rotory" (the source-file spelling) so Rotary and
    # Linear load as separate families. See ELECTRICAL_LINEAR below.
    file_substring="Electrical Actuator Rotory",
    sheet_marker="Electrical Actuator",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # All other catalog fields (Type, Body Material, Enclosure, Application,
    # Certification) have exactly 1 distinct value across all 96 rows, so
    # they're omitted from the cascade — they appear in the detail table only.
    cascade=[
        ("model",   5, "Model"),
        ("voltage", 6, "Voltage"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator"), (3, "Make"), (4, "Type"), (5, "Model"),
        (6, "Voltage"), (7, "Movement"),
        (8, "Body Material"), (9, "O-Ring Material"), (10, "Temperature Rating"),
        (11, "Power Consumption (W)"), (12, "Open-to-Close Time (s)"),
        (13, "Enclosure Protection"), (14, "Actuator Orientation"),
        (15, "Application"), (16, "Painting"), (17, "Certification"),
        (21, "Shaft Female"), (22, "PCD"),
        (23, "Torque (N·m)"), (24, "Weight (kg)"),
    ],
    # NOTE: Actuator.xlsx's 'Working' sheet contains 2 codes not in this catalog
    # (E021GN02, E021GX02 = EA-21/E "with Potentiometer" @ 110 VAC 50/60 Hz). They
    # were NOT folded in: E021GN02 collides with E021GN01 on Model+Voltage (the
    # only cascade fields), and the source is a combined working template whose
    # columns don't map cleanly to this catalog. If these variants are needed,
    # add them to the authoritative datasheet with a distinguishing attribute.
)


ELECTRICAL_LINEAR = ValveTypeConfig(
    key="electrical_linear",
    label="Linear",
    category="Actuators",
    subgroup="Electrical",
    file_substring="Electrical Actuator Linear",
    sheet_marker="Electrical Actuator",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # 40 rows. Model (8 distinct) + Voltage (5) are the only meaningful
    # disambiguators; "Additional Sp 1" (ONF vs with-Potentiometer) added so
    # potentiometer variants don't collide on Model+Voltage.
    cascade=[
        ("model",   5, "Model"),
        ("voltage", 6, "Voltage"),
        ("variant", 18, "Variant"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator"), (3, "Make"), (4, "Type"), (5, "Model"),
        (6, "Voltage"), (8, "Body Material"), (10, "Temperature Rating"),
        (11, "Power Consumption (W)"), (12, "Open-to-Close Time (s)"),
        (13, "Enclosure Protection"), (15, "Application"), (16, "Painting"),
        (17, "Certification"), (18, "Variant"),
        (22, "Maximum Stroke (mm)"), (24, "Weight (kg)"), (25, "Force (kN)"),
    ],
)


PNEUMATIC_CY = ValveTypeConfig(
    key="pneumatic_cy",
    label="CY Series",
    category="Actuators",
    subgroup="Pneumatic Rotary",
    file_substring="CY Series",
    sheet_marker="Sheet2",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # 98 rows; Model is effectively unique. Action (NC/NO) is the only other
    # varying field — everything else is uniform across the series.
    cascade=[
        ("model",  5, "Model"),
        ("action", 4, "Action"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator Type"), (3, "Make"), (4, "Action"),
        (5, "Model"), (7, "Movement"), (8, "Body/Bonnet Material"),
        (9, "O-Ring Material"), (10, "Temperature Rating"),
        (11, "Min Pneumatic Supply"), (12, "Max Pneumatic Supply"),
        (13, "Pneumatic Connections"), (18, "Leakage Class"),
    ],
)


PNEUMATIC_K = ValveTypeConfig(
    key="pneumatic_k",
    label="K Series",
    category="Actuators",
    subgroup="Pneumatic Rotary",
    file_substring="K Series",
    sheet_marker="K-Series",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # 143 rows; Model is unique. Action (NC/NO) and Body Material (3 grades)
    # narrow the model list. Col 2 carries 4 handwheel-variant descriptions.
    cascade=[
        ("model",         5, "Model"),
        ("action",        4, "Action"),
        ("body_material", 8, "Body Material"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator"), (3, "Make"), (4, "Action"), (5, "Model"),
        (7, "Movement"), (8, "Body/Bonnet Material"), (9, "O-Ring Material"),
        (10, "Temperature Rating"), (11, "Min Pneumatic Supply"),
        (12, "Max Pneumatic Supply"), (13, "Pneumatic Connections"),
    ],
)


PNEUMATIC_M = ValveTypeConfig(
    key="pneumatic_m",
    label="M Series",
    category="Actuators",
    subgroup="Pneumatic Rotary",
    file_substring="M Series",
    sheet_marker="Sheet2",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # 8 rows; only Model varies (all other columns uniform).
    cascade=[
        ("model", 5, "Model"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator"), (3, "Make"), (4, "Type"), (5, "Model"),
        (7, "Movement"), (8, "Body/Bonnet Material"), (9, "O-Ring Material"),
        (10, "Temperature Rating"), (11, "Min Pneumatic Supply"),
        (12, "Max Pneumatic Supply"), (13, "Pneumatic Connections"),
    ],
)


MANUAL_HANDWHEEL = ValveTypeConfig(
    key="manual_handwheel",
    label="Manual Handwheel (MPW)",
    category="Actuators",
    subgroup="Manual",
    file_substring="Manual Handwheel",
    sheet_marker="Sheet2",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # 44 rows; Model is unique. Type (Plastic vs Stainless Steel handwheel) is
    # the one other varying field. This family realizes the planned "Manual"
    # subgroup placeholder under Actuators.
    cascade=[
        ("model",   5, "Model"),
        ("variant", 2, "Type"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator"), (3, "Make"), (4, "Type"), (5, "Model"),
        (7, "Movement"), (8, "Body/Bonnet Material"), (9, "O-Ring Material"),
        (10, "Temperature Rating"),
    ],
)


PNEUMATIC_HA = ValveTypeConfig(
    key="pneumatic_ha",
    label="Linear (HA Series)",
    category="Actuators",
    subgroup="Pneumatic Linear",
    file_substring="HA Series",
    sheet_marker="Sheet2",
    primary_label="Code", primary_col=1,
    secondary_label="Model", secondary_col=5,
    show_bto_fos=False,
    # 6 rows (HA-85/110/125 in NC & NO). Same CY/M-Series layout. Model is the
    # unique key; Action (NC/NO) is the only other varying field. This is the
    # "Linear (5-6 bar)" actuator referenced by PHARMA_VALVE's recommendation
    # chip — wiring that chip to target_type="pneumatic_ha" makes it clickable.
    cascade=[
        ("model",  5, "Model"),
        ("action", 4, "Action"),
    ],
    detail_columns=[
        (1, "Code"), (2, "Actuator Type"), (3, "Make"), (4, "Action"),
        (5, "Model"), (7, "Movement"), (8, "Body/Bonnet Material"),
        (9, "O-Ring Material"), (10, "Temperature Rating"),
        (11, "Min Pneumatic Supply"), (12, "Max Pneumatic Supply"),
        (13, "Pneumatic Connections"), (18, "Leakage Class"),
    ],
)


CONTROL_VALVE = ValveTypeConfig(
    key="control_valve",
    label="Control Valve",
    category="Valves",
    subgroup="Pune",
    file_substring="Control Valve Dashboard",
    path_contains="Pune",
    sheet_marker="Control Valve",
    # Power-Query layout: c1 is the table-name column ("…CV"), so Bare Valve
    # Code is c2 and Catalogue is c3 (same shape as PHARMA_VALVE).
    primary_label="Bare Valve Code", primary_col=2,
    secondary_label="Catalogue Code", secondary_col=3,
    show_bto_fos=False,
    # 16,406 rows → 1,991 Catalogue specs (≈8 Bare serials each). Control valves
    # are high-dimensional: this 16-field spec cascade resolves the Catalogue
    # code UNIQUELY (0 ambiguous); within a spec, up to ~5 Bare serials remain
    # (they differ only in test/cost columns not exposed here). Fewer fields
    # leaves catalogues ambiguous; trim only if some attributes are redundant in
    # AVCON's workflow. NOTE: cost/pricing columns (56-59) are deliberately
    # excluded from cascade AND detail so they never reach the public JSON.
    cascade=[
        ("series",          5, "Series"),
        ("size",            6, "Valve Size"),
        ("body_material",   7, "Body Material"),
        ("trim_material",   8, "Trim Material"),
        ("seat_material",   9, "Seat Material"),
        ("characteristics", 10, "Characteristics"),
        ("end_connection",  11, "End Connections"),
        ("valve_type",      12, "Valve Type"),
        ("port_size",       15, "Port Size (mm)"),
        ("num_ports",       16, "No. Of Ports"),
        ("body_style",      18, "Body Style"),
        ("flow_direction",  19, "Flow Direction"),
        ("bonnet_material", 20, "Bonnet Material"),
        ("bonnet_type",     21, "Type Of Bonnet"),
        ("stem_material",   22, "Stem Material"),
        ("plug_type",       23, "Plug Type"),
    ],
    detail_columns=[
        (2, "Bare Valve Code"), (3, "Catalogue Code"), (4, "Make"),
        (5, "Series"), (6, "Valve Size"), (7, "Body Material"),
        (8, "Trim Material"), (9, "Seat Material"), (10, "Characteristics"),
        (11, "End Connections"), (12, "Valve Type"), (13, "Design Standard"),
        (14, "Face to Face"), (15, "Port Size (mm)"), (16, "No. Of Ports"),
        (17, "Valve Kv (m³/hr)"), (18, "Body Style"), (19, "Flow Direction"),
        (20, "Bonnet Material"), (21, "Type Of Bonnet"), (22, "Stem Material"),
        (23, "Plug Type"), (24, "Gland Packing"), (25, "Body Packing"),
        (26, "Flange Dimensions"), (27, "Flange Drilling"), (28, "Pressure Rating"),
        (29, "Operating Temp Range (°C)"), (30, "Hardware"), (31, "Valve Paint"),
        (32, "Testing Standard"), (33, "Leakage Class"),
        (34, "Body Test Pressure (barg)"), (35, "Body Test Media"),
        (36, "Seat Leakage Test Pressure (barg)"), (37, "Seat Leakage Test Media"),
        (38, "Product Group"), (39, "Certification"), (40, "Thrust (kN)"),
        (41, "Torque (N·m)"), (42, "Mounting PCD"), (43, "Stroke (mm)"),
        (44, "Stem Diameter"), (55, "Bare Valve Weight (kg)"),
    ],
)


VALVE_TYPES: list[ValveTypeConfig] = [
    BALL_VALVE,
    BUTTERFLY_VALVE,
    PHARMA_VALVE,
    CONTROL_VALVE,
    PNEUMATIC_RACK_PINION,
    PNEUMATIC_SCOTCH_YOKE,
    PNEUMATIC_CY,
    PNEUMATIC_K,
    PNEUMATIC_M,
    PNEUMATIC_HA,
    ELECTRICAL_ROTARY,
    ELECTRICAL_LINEAR,
    MANUAL_HANDWHEEL,
]


# Subgroups that should appear in a category's picker menu even before any
# catalog populates them. Each entry: category -> ordered list of
# (subgroup_name, placeholder_text). Auto-superseded once a real family loads
# into the subgroup (see build_category_blocks). Only injected into categories
# that already have at least one loaded family.
PLANNED_SUBGROUPS: dict[str, list[tuple[str, str]]] = {
    "Valves": [("Mumbai", "Data pending — Mumbai catalog coming soon")],
    # Manual (SHL) is a distinct, hand-operated actuator family referenced by
    # Pharma valves; its catalog is pending (data/Actuator/Manual Actuator) and
    # shows as a placeholder subgroup until supplied.
    # Linear (HA-*, 5-6 bar) is NOT a browsable family — it's a pneumatic
    # operation type, surfaced as a chip in each valve's Recommended Actuator
    # list (see PHARMA_VALVE.paired_actuators), so it has no picker subgroup.
    "Actuators": [
        ("Manual", "Data pending — Manual actuator catalog coming soon"),
    ],
}


def _norm(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip().replace("\xa0", "")
        return s if s else None
    return v


import re

# TRANSITIONAL: source-data format drift between per-series files and the
# destination actuator catalogs. Two patterns observed (2026-05-26 +
# 2026-05-27 validation reports):
#   (1) Missing dash after letter prefix:
#         `SYA065300DAS` (per-series)  vs  `SYA-065300DAS` (SY catalog)
#   (2) Missing slash before trailing single letter:
#         `EA-21D` (per-series)  vs  `EA-21/D` (electrical_rotary catalog)
#         `QM-150D` (per-series)  vs  `QM-150/D` (electrical_rotary catalog)
# We normalize at load time so lookups succeed even when engineering hasn't
# yet cleaned the source files. Remove when source data is consistent.
_PAIRED_MODEL_DASH_PREFIXES = ("SYA",)
_EA_QM_SLASH_PATTERN = re.compile(r"^(EA|QM)-(\d+)([A-Z])$")


def _normalize_paired_model(model: str) -> str:
    """Apply known format-drift corrections so the recommended-model string
    matches the canonical form used in the destination actuator catalog."""
    # Pattern 1: insert missing dash after prefix (SYA065 -> SYA-065)
    for prefix in _PAIRED_MODEL_DASH_PREFIXES:
        if model.startswith(prefix) and not model.startswith(f"{prefix}-"):
            model = f"{prefix}-{model[len(prefix):]}"
            break
    # Pattern 2: insert missing slash before trailing letter (EA-21D -> EA-21/D)
    m = _EA_QM_SLASH_PATTERN.match(model)
    if m:
        return f"{m.group(1)}-{m.group(2)}/{m.group(3)}"
    return model


class Catalog:
    def __init__(self, config: ValveTypeConfig, file_path: Path, data_dir: Path | None = None):
        self.config = config
        self.file_path = file_path
        # Root used to resolve extra_row_sources (which may live in a different
        # subfolder than this catalog's file). Defaults to the file's parent.
        self.data_dir = data_dir if data_dir is not None else file_path.parent
        self.rows: list[dict[str, Any]] = []
        self._key_to_col = {k: idx for k, idx, _ in config.cascade}
        self._load()

    def _load(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                wb = openpyxl.load_workbook(
                    self.file_path, data_only=True, keep_vba=False, read_only=True
                )
            except PermissionError:
                # File is locked (almost always Excel has it open). Copy to a
                # temp file and read from there so the app launches anyway.
                tmp_dir = Path(tempfile.gettempdir()) / "valve-selector-cache"
                tmp_dir.mkdir(exist_ok=True)
                tmp_path = tmp_dir / self.file_path.name
                shutil.copyfile(self.file_path, tmp_path)
                print(
                    f"[valve-selector] {self.file_path.name} is locked "
                    f"(Excel has it open). Loading from temp copy."
                )
                wb = openpyxl.load_workbook(
                    tmp_path, data_only=True, keep_vba=False, read_only=True
                )

        sheet_names = [s for s in wb.sheetnames if self.config.sheet_marker in s]
        if not sheet_names:
            raise RuntimeError(
                f"No catalog sheets in {self.file_path.name} matching "
                f"marker {self.config.sheet_marker!r}."
            )

        max_col = max(
            max(idx for _, idx, _ in self.config.cascade),
            max(idx for idx, _ in self.config.detail_columns),
            self.config.primary_col,
            self.config.secondary_col or 0,
            self.config.bto_col if self.config.show_bto_fos else 0,
        )

        # Skip rows whose PRIMARY code column is empty. For ball/butterfly/
        # actuators primary_col is 1 (same as the old `not raw[0]` check); for
        # Pharma the real code is c2 (c1 is a Power-Query "Name" column), so this
        # drops the 728 blank-code spacer rows that would otherwise load as
        # ghost SKUs with no Bare Valve Code.
        key_idx = self.config.primary_col - 1
        for sn in sheet_names:
            ws = wb[sn]
            # Capture the primary-column header (row 1) so we can drop any
            # REPEATED header rows embedded mid-data. Some source workbooks
            # (e.g. Control Valve Dashboard, concatenated from several
            # Power-Query exports) carry the header line many times — at rows
            # 643/964/1285/… as well as row 1. Without this they load as ghost
            # rows whose every cell is the column label ("Bare Valve Code" =
            # "Bare Valve Code"), polluting every dropdown with a junk option.
            # Real codes never equal the header text, so this is safe for all
            # catalogs.
            header_key = None
            for r_i, raw in enumerate(ws.iter_rows(min_row=1, max_col=max_col, values_only=True)):
                if not raw or key_idx >= len(raw):
                    continue
                key_val = _norm(raw[key_idx])
                if r_i == 0:  # header row
                    header_key = (
                        str(key_val).strip().lower()
                        if key_val not in (None, "") else None
                    )
                    continue
                if key_val in (None, ""):
                    continue
                if header_key is not None and str(key_val).strip().lower() == header_key:
                    continue  # repeated header row embedded in the data
                row = {f"c{i+1}": _norm(v) for i, v in enumerate(raw)}
                self.rows.append(row)

        if not self.rows:
            raise RuntimeError(
                f"{self.file_path.name} parsed but contained no rows under "
                f"marker {self.config.sheet_marker!r}."
            )

        for src in self.config.enrichment_sources:
            self._apply_enrichment(src)

        for src in self.config.extra_row_sources:
            self._apply_extra_rows(src)

    def _apply_extra_rows(self, src: ExtraRowSource) -> None:
        """Append rows from `src` whose key isn't already in self.rows, remapping
        source columns to catalog columns via src.column_map. Non-destructive."""
        try:
            src_path = find_catalog_file(self.data_dir, src.file_substring, src.path_contains)
        except FileNotFoundError:
            print(
                f"[valve-selector]   extra-rows skipped for {self.config.key}: "
                f"no file matching '*{src.file_substring}*'.",
                flush=True,
            )
            return

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                wb = openpyxl.load_workbook(
                    src_path, data_only=True, keep_vba=False, read_only=True
                )
            except PermissionError:
                tmp_dir = Path(tempfile.gettempdir()) / "valve-selector-cache"
                tmp_dir.mkdir(exist_ok=True)
                tmp_path = tmp_dir / src_path.name
                shutil.copyfile(src_path, tmp_path)
                wb = openpyxl.load_workbook(
                    tmp_path, data_only=True, keep_vba=False, read_only=True
                )

        sheet_names = [s for s in wb.sheetnames if src.sheet_marker in s]
        if not sheet_names:
            wb.close()
            print(
                f"[valve-selector]   extra-rows skipped: no sheet matching "
                f"{src.sheet_marker!r} in {src_path.name}.",
                flush=True,
            )
            return

        pat = re.compile(src.key_pattern) if src.key_pattern else None
        master_key = f"c{src.master_key_col}"
        existing = {
            str(_norm(r.get(master_key))).strip()
            for r in self.rows if r.get(master_key) not in (None, "")
        }
        max_col = max(src.key_col, max(s for s, _ in src.column_map))
        added = 0
        for sn in sheet_names:
            for raw in wb[sn].iter_rows(min_row=2, max_col=max_col, values_only=True):
                if not raw or src.key_col - 1 >= len(raw):
                    continue
                key = _norm(raw[src.key_col - 1])
                if key in (None, ""):
                    continue
                key = str(key).strip()
                if pat and not pat.match(key):
                    continue          # header/garbage row
                if key in existing:
                    continue          # SKU already in the catalog
                row = {}
                for s_col, m_col in src.column_map:
                    row[f"c{m_col}"] = _norm(raw[s_col - 1]) if s_col - 1 < len(raw) else None
                self.rows.append(row)
                existing.add(key)
                added += 1
        wb.close()
        print(
            f"[valve-selector]   added {added} extra rows from {src_path.name}.",
            flush=True,
        )

    def _apply_enrichment(self, src: EnrichmentSource) -> None:
        """Pull extra columns from `src` and merge into self.rows by join key."""
        try:
            src_path = find_catalog_file(self.file_path.parent, src.file_substring)
        except FileNotFoundError:
            print(
                f"[valve-selector]   enrichment skipped for {self.config.key}: "
                f"no file matching '*{src.file_substring}*'.",
                flush=True,
            )
            return

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                wb = openpyxl.load_workbook(
                    src_path, data_only=True, keep_vba=False, read_only=True
                )
            except PermissionError:
                tmp_dir = Path(tempfile.gettempdir()) / "valve-selector-cache"
                tmp_dir.mkdir(exist_ok=True)
                tmp_path = tmp_dir / src_path.name
                shutil.copyfile(src_path, tmp_path)
                wb = openpyxl.load_workbook(
                    tmp_path, data_only=True, keep_vba=False, read_only=True
                )

        sheet_names = [s for s in wb.sheetnames if src.sheet_marker in s]
        if not sheet_names:
            print(
                f"[valve-selector]   enrichment skipped: no sheet matching "
                f"{src.sheet_marker!r} in {src_path.name}.",
                flush=True,
            )
            return

        max_col = max(src.source_key_col, max(s for s, _ in src.columns))
        lookup: dict[Any, dict[int, Any]] = {}
        for sn in sheet_names:
            ws = wb[sn]
            for raw in ws.iter_rows(min_row=2, max_col=max_col, values_only=True):
                if not raw:
                    continue
                key = _norm(raw[src.source_key_col - 1])
                if key is None:
                    continue
                lookup[key] = {
                    dest: _norm(raw[s - 1]) for s, dest in src.columns
                }

        master_key = f"c{src.master_key_col}"
        hits = 0
        for row in self.rows:
            mk = row.get(master_key)
            if mk is None:
                continue
            extra = lookup.get(mk)
            if not extra:
                continue
            for dest, val in extra.items():
                if val is None:
                    continue
                row[f"c{dest}"] = val
            hits += 1
        print(
            f"[valve-selector]   enriched {hits} rows from {src_path.name}.",
            flush=True,
        )

    def _filter(self, picks: dict[str, Any]) -> list[dict[str, Any]]:
        if not picks:
            return self.rows
        out = []
        for row in self.rows:
            ok = True
            for key, val in picks.items():
                col = self._key_to_col.get(key)
                if col is None:
                    continue
                if str(row.get(f"c{col}")) != str(val):
                    ok = False
                    break
            if ok:
                out.append(row)
        return out

    def options(self, picks: dict[str, Any]) -> dict[str, list[str]]:
        matched = self._filter(picks)
        out: dict[str, list[str]] = {}
        for key, col, _ in self.config.cascade:
            if key in picks:
                continue
            vals = {row.get(f"c{col}") for row in matched}
            vals.discard(None)
            out[key] = sorted(vals, key=lambda v: (len(str(v)), str(v)))
        return out

    def resolve(self, picks: dict[str, Any]) -> dict[str, Any] | None:
        matched = self._filter(picks)
        if not matched:
            return None
        row = matched[0]
        detail: dict[str, Any] = {
            "match_count": len(matched),
            "fields": [
                {"label": label, "value": row.get(f"c{col}")}
                for col, label in self.config.detail_columns
            ],
            "primary": row.get(f"c{self.config.primary_col}"),
            "secondary": (
                row.get(f"c{self.config.secondary_col}")
                if self.config.secondary_col else None
            ),
        }
        if self.config.show_bto_fos:
            bto = row.get(f"c{self.config.bto_col}")
            detail["bto"] = bto
            try:
                detail["fos"] = float(bto) * 1.5 if bto not in (None, "") else None
            except (TypeError, ValueError):
                detail["fos"] = None
        paired_list = []
        # Dedup rule (user's choice 2026-06-04):
        #   * DOUBLE-ACTING pressure slots (label has BOTH "Double Acting" and
        #     "@ … bar", e.g. Ball's DA @3.5/@4/@5.5) show every pressure even
        #     when the SAME model repeats — so a valve whose DA actuator is
        #     ACT-050D at all three pressures shows THREE chips.
        #   * EVERYTHING ELSE (Spring-Return at any pressure, Electric, Linear,
        #     and the generic "alternative" columns) dedupes by code: one chip
        #     per distinct (target_type, model). This keeps Spring-Return from
        #     repeating the same code across pressures, while still surfacing
        #     genuinely new alternatives (e.g. ACT-063SR07).
        seen_models = set()  # (target_type, model) shown so far
        seen_slots = set()   # (target_type, model, label) — exact DA pressure-slot twins
        for p in self.config.paired_actuators:
            paired_val = row.get(f"c{p.model_col}")
            if paired_val in (None, ""):
                continue
            model = _normalize_paired_model(str(paired_val).strip())
            # `#N/A` is an Excel error string from broken VLOOKUP cells in the
            # source — treat as no recommendation (see 2026-05-27 report).
            if model in ("", "#N/A"):
                continue
            target_type = p.resolve_target_type(model)
            if "Double Acting" in p.label and "@" in p.label:   # DA pressure slot — keep each pressure
                slot = (target_type, model, p.label)
                if slot in seen_slots:
                    continue
                seen_slots.add(slot)
            elif (target_type, model) in seen_models:            # everything else — one chip per code
                continue
            seen_models.add((target_type, model))
            paired_list.append({
                "model": model,
                "target_type": target_type,
                "target_field": p.target_field,
                "label": p.label,
            })
        if paired_list:
            detail["paired_actuators"] = paired_list
        return detail

    def cascade(self) -> list[dict[str, str]]:
        return [{"key": k, "label": label} for k, _idx, label in self.config.cascade]


def find_catalog_file(
    data_dir: Path, file_substring: str, path_contains: str | None = None
) -> Path:
    """Pick the most recently modified .xlsx/.xlsm under `data_dir` (recursively)
    whose name contains `file_substring`. Walking recursively lets the catalog
    files live in nested subfolders (e.g. `data/Valve/Ball Valve Data Set/`).

    `path_contains` optionally restricts matches to files whose full path
    contains that fragment — used to disambiguate same-named files in different
    subfolders (e.g. the Pune vs Mumbai `Valve_Code_Selector_Dashboard.xlsx`)."""
    def _path_ok(p: Path) -> bool:
        if path_contains is None:
            return True
        return path_contains in str(p).replace("\\", "/")

    candidates = [
        p for p in data_dir.rglob("*.xls*")
        if file_substring in p.name and not p.name.startswith("~$") and _path_ok(p)
    ]
    if not candidates:
        scope = f" (path containing '{path_contains}')" if path_contains else ""
        raise FileNotFoundError(
            f"No file matching '*{file_substring}*'{scope} under {data_dir}."
        )
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def build_category_blocks(sections, planned_subgroups=None):
    """Group section summaries into category -> ordered subgroups for the picker.

    Each returned block: {"name": <category>, "subgroups": [
        {"name": <subgroup>, "members": [<section>...], "placeholder": <str>}]}.

    `planned_subgroups` (category -> [(subgroup_name, placeholder_text), ...])
    appends subgroups that have no loaded members yet, carrying placeholder text
    the template renders as a non-selectable row. A planned subgroup that already
    has loaded members is left untouched (real data wins). Planned entries for a
    category with no loaded sections are skipped — a placeholder needs a picker,
    and the picker only exists when the category has at least one family.
    """
    planned_subgroups = planned_subgroups or {}
    categories: "OrderedDict[str, OrderedDict[str, list]]" = OrderedDict()
    for sec in sections:
        cat_key = sec["category"]
        if cat_key not in categories:
            categories[cat_key] = OrderedDict()
        sub = sec.get("subgroup") or ""
        categories[cat_key].setdefault(sub, []).append(sec)

    blocks = []
    for cat_name, subgroups in categories.items():
        block_subgroups = [
            {"name": name, "members": members, "placeholder": ""}
            for name, members in subgroups.items()
        ]
        for sub_name, placeholder in planned_subgroups.get(cat_name, []):
            if sub_name in subgroups:
                continue  # already has real members
            block_subgroups.append(
                {"name": sub_name, "members": [], "placeholder": placeholder}
            )
        blocks.append({"name": cat_name, "subgroups": block_subgroups})
    return blocks


def load_all(data_dir: Path) -> dict[str, Catalog]:
    out: dict[str, Catalog] = {}
    for cfg in VALVE_TYPES:
        try:
            path = find_catalog_file(data_dir, cfg.file_substring, cfg.path_contains)
        except FileNotFoundError:
            print(f"[valve-selector] Skipping {cfg.key}: no file matching '*{cfg.file_substring}*'.", flush=True)
            continue
        print(f"[valve-selector] Loading {cfg.key} catalog from {path.name}...", flush=True)
        out[cfg.key] = Catalog(cfg, path, data_dir)
        print(f"[valve-selector]   loaded {len(out[cfg.key].rows)} {cfg.key} rows.", flush=True)
    if not out:
        raise RuntimeError(f"No catalog files found in {data_dir}.")
    return out
