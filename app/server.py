"""Flask app for the multi-type product code selector.

Loads every registered product-type catalog at startup. The UI renders ONE
picker widget per category (Valves, Actuators, …). API endpoints are
namespaced by product-type key (/api/<type>/options, /api/<type>/resolve).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import webbrowser
from collections import OrderedDict
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from catalog import load_all  # noqa: E402
from accessories import load_accessories  # noqa: E402

PROJECT_ROOT = HERE.parent
DATA_DIR = PROJECT_ROOT / "data"
PORT = 5037

app = Flask(__name__, template_folder=str(HERE / "templates"), static_folder=str(HERE / "static"))

print(f"[valve-selector] Loading catalogs from {DATA_DIR}...", flush=True)
CATALOGS = load_all(DATA_DIR)
print(f"[valve-selector] Ready: {', '.join(CATALOGS.keys())}", flush=True)

# Accessories are a separate flat list (not a cascade catalog) — see
# accessories.py for why. Empty {} if no file present.
ACCESSORIES = load_accessories(DATA_DIR)


def _parse_picks() -> dict[str, str]:
    raw = request.args.get("picks", "").strip()
    if not raw:
        return {}
    try:
        picks = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(picks, dict):
        return {}
    return {k: v for k, v in picks.items() if v not in (None, "")}


def _get_catalog(valve_type: str):
    cat = CATALOGS.get(valve_type)
    if cat is None:
        abort(404, description=f"Unknown product type: {valve_type}")
    return cat


def _section_summary(key: str, cat) -> dict:
    cfg = cat.config
    return {
        "key": key,
        "label": cfg.label,
        "category": cfg.category,
        "subgroup": cfg.subgroup,
        "source_file": cat.file_path.name,
        "row_count": len(cat.rows),
        "cascade": cat.cascade(),
        "primary_label": cfg.primary_label,
        "secondary_label": cfg.secondary_label,
        "show_bto_fos": cfg.show_bto_fos,
    }


@app.route("/")
def index():
    sections = [_section_summary(k, c) for k, c in CATALOGS.items()]

    # Group sections by category (preserves first-appearance order), then by
    # subgroup within each category.
    categories: "OrderedDict[str, dict]" = OrderedDict()
    for sec in sections:
        cat_key = sec["category"]
        if cat_key not in categories:
            categories[cat_key] = {"name": cat_key, "subgroups": OrderedDict()}
        sub = sec["subgroup"] or ""
        categories[cat_key]["subgroups"].setdefault(sub, []).append(sec)

    # Flatten the OrderedDicts into lists for the Jinja loop
    category_blocks = []
    for cat in categories.values():
        category_blocks.append({
            "name": cat["name"],
            "subgroups": [
                # NB: avoid the key name "items" — Jinja resolves `.items` to the
                # dict method first, shadowing any 'items' key in the data.
                {"name": k, "members": v} for k, v in cat["subgroups"].items()
            ],
        })

    total_skus = sum(sec["row_count"] for sec in sections)
    return render_template(
        "index.html",
        sections=sections,
        category_blocks=category_blocks,
        total_skus=total_skus,
        accessories_summary={
            "row_count": len(ACCESSORIES.get("rows", [])),
            "family_count": len(ACCESSORIES.get("families", [])),
            "source_file": ACCESSORIES.get("source_file"),
        },
    )


@app.route("/api/accessories/list")
def api_accessories_list():
    """Returns the full accessory list grouped by family. The UI does its
    own filtering / search client-side so we ship everything once."""
    return jsonify({
        "rows": ACCESSORIES.get("rows", []),
        "families": ACCESSORIES.get("families", []),
        "source_file": ACCESSORIES.get("source_file"),
    })


@app.route("/api/<valve_type>/options")
def api_options(valve_type: str):
    return jsonify(_get_catalog(valve_type).options(_parse_picks()))


@app.route("/api/<valve_type>/resolve")
def api_resolve(valve_type: str):
    detail = _get_catalog(valve_type).resolve(_parse_picks())
    if detail is None:
        return jsonify({"matched": False})
    for paired in detail.get("paired_actuators", []):
        target_cat = CATALOGS.get(paired["target_type"])
        if target_cat is None:
            # target_type is None (no prefix matched) or names an unknown
            # catalog. The recommended model has nowhere to land.
            paired["name"] = None
            paired["not_in_catalog"] = True
            continue
        found, name = _lookup_paired(
            target_cat, paired["target_field"], paired["model"]
        )
        paired["name"] = name
        paired["not_in_catalog"] = not found
    return jsonify({"matched": True, "detail": detail})


def _lookup_paired(target_cat, field_key: str, model_value: str) -> tuple[bool, str | None]:
    """Look up `model_value` in `target_cat` by the cascade column for
    `field_key`. Returns (found, friendly_name). `found=False` flags a data
    gap (model recommended by a valve but missing from the destination
    actuator catalog — see Issue 3 in the 2026-05-26 validation report).
    `name=None` with `found=True` means the row exists but has no
    Actuator/Type detail columns to build a name from (config gap, not data)."""
    col = target_cat._key_to_col.get(field_key)
    if not col:
        return False, None
    for row in target_cat.rows:
        if str(row.get(f"c{col}")) != str(model_value):
            continue
        wanted = {"Actuator", "Type"}
        parts = []
        for c, label in target_cat.config.detail_columns:
            if label in wanted:
                v = row.get(f"c{c}")
                if v:
                    parts.append(str(v).strip())
        return True, (" — ".join(parts) if parts else None)
    return False, None


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "types": {
            k: {
                "rows": len(c.rows),
                "category": c.config.category,
                "subgroup": c.config.subgroup,
                "source": c.file_path.name,
            } for k, c in CATALOGS.items()
        },
    })


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}"
    print(f"[valve-selector] Listening on {url}", flush=True)
    print("[valve-selector] Close this window to stop the server.", flush=True)
    if os.environ.get("VALVE_SELECTOR_NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open_new(url)).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
