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


BALL_VALVE = ValveTypeConfig(
    key="ball",
    label="Ball Valve",
    category="Valves",
    file_substring="Ball Valve",
    sheet_marker="BV NEW CODEING",
    # Recommended actuators per SKU. As of 2026-05-27, the richer source is
    # the dashboard file's "Ball Valve Actuator combination" sheet — it carries
    # pressure-specific labels (3.5/4/5.5 bar) for the 9 pneumatic positions
    # AND the 2 electric positions. The enrichment below pulls source cols
    # 49-59 into master cols 100-110, and these entries read the enriched cols.
    # Dedup is by (target_type, model, label), so a model valid at multiple
    # pressures (common: ACT-050D works at 3.5, 4, AND 5.5 bar) surfaces one
    # chip per pressure — matching the column count in the source sheet.
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
        # Electrical — same label on both chips so the JS group heading reads
        # "Option N — Electrical" and each chip's sub-line shows "Electrical".
        # (Stripping only happens when the label has an em dash like
        # "Pneumatic — Double Acting"; plain "Electrical" passes through.)
        PairedActuator(model_col=109, target_type="electrical_rotary", target_field="model",
                       label="Electrical"),
        PairedActuator(model_col=110, target_type="electrical_rotary", target_field="model",
                       label="Electrical"),
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
    ],
    # Single enrichment source — the new dashboard file's "Ball Valve Actuator
    # combination" sheet (added 2026-05-27). It carries all 11 actuator
    # positions (9 pneumatic at varying pressures, 2 electric) for every Bare
    # Valve Code in the catalog. Replaces the 4 per-series enrichments we
    # previously used (which only carried the 2 electric columns and required
    # 4 separate files).
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
    ),
)


BUTTERFLY_VALVE = ValveTypeConfig(
    key="butterfly",
    label="Butterfly Valve (Centric)",
    category="Valves",
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
        # Electrical — single-target (all values are EA-* or QM-*, both in
        # electrical_rotary catalog). Plain "Electrical" label reaches the
        # chip's sub-line unchanged since there's no em dash for the JS
        # prefix regex to strip.
        PairedActuator(
            model_col=109, target_type="electrical_rotary", target_field="model",
            label="Electrical",
        ),
        PairedActuator(
            model_col=110, target_type="electrical_rotary", target_field="model",
            label="Electrical",
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
    subgroup="Pneumatic",
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
    subgroup="Pneumatic",
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
    file_substring="Electrical Actuator",
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
        # Col 18 is mislabeled "Additional Sp 1" in the source header, but
        # carries a real feature flag for all 96 rows (values: ONF or
        # 'with Potentiometer'). Surfacing it as Additional Specification.
        (18, "Additional Specification"),
        (21, "Shaft Female"), (22, "PCD"),
        (23, "Torque (N·m)"), (24, "Weight (kg)"),
    ],
)


VALVE_TYPES: list[ValveTypeConfig] = [
    BALL_VALVE,
    BUTTERFLY_VALVE,
    PNEUMATIC_RACK_PINION,
    PNEUMATIC_SCOTCH_YOKE,
    ELECTRICAL_ROTARY,
]


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
    def __init__(self, config: ValveTypeConfig, file_path: Path):
        self.config = config
        self.file_path = file_path
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

        for sn in sheet_names:
            ws = wb[sn]
            for raw in ws.iter_rows(min_row=2, max_col=max_col, values_only=True):
                if not raw or not raw[0]:
                    continue
                row = {f"c{i+1}": _norm(v) for i, v in enumerate(raw)}
                self.rows.append(row)

        if not self.rows:
            raise RuntimeError(
                f"{self.file_path.name} parsed but contained no rows under "
                f"marker {self.config.sheet_marker!r}."
            )

        for src in self.config.enrichment_sources:
            self._apply_enrichment(src)

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
        # Dedupe on (target_type, model, label). Keying on the LABEL too means a
        # model recommended at several pressures (e.g. ACT-050D Double-Acting at
        # 3.5/4/5.5 bar) surfaces one chip PER pressure — the column count the
        # user expects — while truly identical positions (same model AND label,
        # e.g. the two "Electrical" cols 109/110 holding the same model) still
        # collapse to one chip so the panel never shows a pixel-identical twin.
        seen_keys = set()
        for p in self.config.paired_actuators:
            paired_val = row.get(f"c{p.model_col}")
            raw = "" if paired_val is None else str(paired_val).strip()
            model = _normalize_paired_model(raw)
            # The ball-valve actuator-combination sheet uses sentinels for "no
            # actuator at this pressure": empty cells, literal 0 (~1,176 rows at
            # 5.5 bar), and broken VLOOKUPs (#N/A/#REF!/#VALUE!). Rather than
            # drop them, emit a placeholder entry (empty=True, model=None) so the
            # panel renders the position as a greyed 'not available' slot.
            if model in ("", "0", "#N/A", "#REF!", "#VALUE!"):
                empty_key = ("empty", p.label)
                if empty_key in seen_keys:
                    continue
                seen_keys.add(empty_key)
                paired_list.append({
                    "model": None,
                    "target_type": p.target_type,
                    "target_field": p.target_field,
                    "label": p.label,
                    "empty": True,
                })
                continue
            target_type = p.resolve_target_type(model)
            key = (target_type, model, p.label)
            if key in seen_keys:
                continue
            seen_keys.add(key)
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


def find_catalog_file(data_dir: Path, file_substring: str) -> Path:
    """Pick the most recently modified .xlsx/.xlsm under `data_dir` (recursively)
    whose name contains `file_substring`. Walking recursively lets the catalog
    files live in nested subfolders (e.g. `data/Valve/Ball Valve Data Set/`)."""
    candidates = [
        p for p in data_dir.rglob("*.xls*")
        if file_substring in p.name and not p.name.startswith("~$")
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No file matching '*{file_substring}*' under {data_dir}."
        )
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def load_all(data_dir: Path) -> dict[str, Catalog]:
    out: dict[str, Catalog] = {}
    for cfg in VALVE_TYPES:
        try:
            path = find_catalog_file(data_dir, cfg.file_substring)
        except FileNotFoundError:
            print(f"[valve-selector] Skipping {cfg.key}: no file matching '*{cfg.file_substring}*'.", flush=True)
            continue
        print(f"[valve-selector] Loading {cfg.key} catalog from {path.name}...", flush=True)
        out[cfg.key] = Catalog(cfg, path)
        print(f"[valve-selector]   loaded {len(out[cfg.key].rows)} {cfg.key} rows.", flush=True)
    if not out:
        raise RuntimeError(f"No catalog files found in {data_dir}.")
    return out
