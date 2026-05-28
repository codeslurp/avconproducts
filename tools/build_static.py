"""Build the static GitHub Pages bundle in docs/.

Reads the .xlsm/.xlsx catalogs from data/ using the existing Flask-app loaders
(app/catalog.py, app/accessories.py) so cascade rules, format-drift fixes, and
enrichment-VLOOKUPs stay in one place. Writes:

  docs/index.html                — pre-rendered from app/templates/index.html
  docs/data/<type>.json          — per-catalog config + rows (compact array form)
  docs/data/accessories.json     — flat accessories list
  docs/static/{styles.css,app.js,avcon-logo.png,catalog-engine.js}

Run from repo root:  py tools/build_static.py
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from collections import OrderedDict
from pathlib import Path

# Build timestamp used to cache-bust asset URLs. GitHub Pages serves CSS/JS
# with long Cache-Control headers we can't override, so old assets linger in
# the browser even after a deploy. Appending ?v=<this> forces a fresh fetch.
# Format YYYYMMDDhhmmss — sorts nicely in DevTools and is one second per build.
BUILD_VERSION = time.strftime("%Y%m%d%H%M%S")

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "app"
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
TEMPLATE_DIR = APP_DIR / "templates"
APP_STATIC = APP_DIR / "static"

sys.path.insert(0, str(APP_DIR))
from catalog import load_all  # noqa: E402
from accessories import load_accessories  # noqa: E402

from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402


def _url_for_stub(endpoint: str, **kwargs) -> str:
    """Replace Flask's url_for at build time.

    Pages serves project sites under /<repo>/ so asset URLs must be RELATIVE
    (no leading slash) to resolve correctly. The browser will join them against
    the current page URL, landing on .../avconproducts/static/styles.css.
    The ?v=BUILD_VERSION query string cache-busts on every build so users
    don't need to hard-refresh after each CSS/JS change."""
    if endpoint == "static":
        return f"static/{kwargs['filename']}?v={BUILD_VERSION}"
    return "#"


def _used_columns(cfg) -> list[int]:
    """Every column the JS engine will need to read for this catalog."""
    cols: set[int] = set()
    for _, col, _ in cfg.cascade:
        cols.add(col)
    for col, _ in cfg.detail_columns:
        cols.add(col)
    cols.add(cfg.primary_col)
    if cfg.secondary_col:
        cols.add(cfg.secondary_col)
    if cfg.show_bto_fos:
        cols.add(cfg.bto_col)
    for pa in cfg.paired_actuators:
        cols.add(pa.model_col)
    return sorted(cols)


def _serialize_catalog(key: str, catalog) -> dict:
    cfg = catalog.config
    used = _used_columns(cfg)
    rows_compact = []
    for row in catalog.rows:
        rows_compact.append([row.get(f"c{c}") for c in used])

    paired = []
    for pa in cfg.paired_actuators:
        paired.append({
            "model_col": pa.model_col,
            "target_field": pa.target_field,
            "label": pa.label,
            "target_type": pa.target_type,
            "target_by_prefix": [list(t) for t in pa.target_type_by_prefix] or None,
        })

    return {
        "key": key,
        "label": cfg.label,
        "category": cfg.category,
        "subgroup": cfg.subgroup,
        "primary_label": cfg.primary_label,
        "primary_col": cfg.primary_col,
        "secondary_label": cfg.secondary_label,
        "secondary_col": cfg.secondary_col,
        "show_bto_fos": cfg.show_bto_fos,
        "bto_col": cfg.bto_col if cfg.show_bto_fos else None,
        "cascade": [{"key": k, "col": c, "label": lab} for k, c, lab in cfg.cascade],
        "detail_columns": [{"col": c, "label": lab} for c, lab in cfg.detail_columns],
        "paired_actuators": paired,
        "columns_used": used,
        "rows": rows_compact,
        "source_file": catalog.file_path.name,
    }


def _section_summary(key: str, catalog) -> dict:
    cfg = catalog.config
    return {
        "key": key,
        "label": cfg.label,
        "category": cfg.category,
        "subgroup": cfg.subgroup,
        "source_file": catalog.file_path.name,
        "row_count": len(catalog.rows),
        "cascade": [{"key": k, "label": lab} for k, _, lab in cfg.cascade],
        "primary_label": cfg.primary_label,
        "secondary_label": cfg.secondary_label,
        "show_bto_fos": cfg.show_bto_fos,
    }


def _category_blocks(sections: list[dict]) -> list[dict]:
    categories: "OrderedDict[str, dict]" = OrderedDict()
    for sec in sections:
        cat_key = sec["category"]
        if cat_key not in categories:
            categories[cat_key] = {"name": cat_key, "subgroups": OrderedDict()}
        sub = sec["subgroup"] or ""
        categories[cat_key]["subgroups"].setdefault(sub, []).append(sec)

    out = []
    for cat in categories.values():
        out.append({
            "name": cat["name"],
            "subgroups": [
                {"name": k, "members": v}
                for k, v in cat["subgroups"].items()
            ],
        })
    return out


def main() -> None:
    print(f"[build] reading catalogs from {DATA_DIR}")
    catalogs = load_all(DATA_DIR)
    accessories = load_accessories(DATA_DIR)

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "data").mkdir(exist_ok=True)
    (DOCS_DIR / "static").mkdir(exist_ok=True)

    # 1. Per-catalog JSON
    for key, cat in catalogs.items():
        out = DOCS_DIR / "data" / f"{key}.json"
        payload = _serialize_catalog(key, cat)
        out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        size_mb = out.stat().st_size / 1_048_576
        print(f"[build]   wrote {out.name} — {len(cat.rows):,} rows, {size_mb:.2f} MB")

    # 2. Accessories
    acc_out = DOCS_DIR / "data" / "accessories.json"
    acc_out.write_text(
        json.dumps(accessories, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"[build]   wrote accessories.json — {len(accessories.get('rows', []))} rows")

    # 3. Static assets. app.js works in BOTH Flask and static modes because
    #    the dataAPI shim at the top of the file detects window.CatalogEngine
    #    at runtime (defined here by catalog-engine.js, undefined under Flask).
    #    So we can copy it straight — same source for both deployments.
    shutil.copy(APP_STATIC / "styles.css", DOCS_DIR / "static" / "styles.css")
    shutil.copy(APP_STATIC / "app.js", DOCS_DIR / "static" / "app.js")
    shutil.copy(APP_STATIC / "avcon-logo.png", DOCS_DIR / "static" / "avcon-logo.png")
    print("[build]   copied styles.css, app.js, avcon-logo.png")

    # 4. Render index.html
    sections = [_section_summary(k, c) for k, c in catalogs.items()]
    blocks = _category_blocks(sections)
    total_skus = sum(s["row_count"] for s in sections)
    acc_summary = {
        "row_count": len(accessories.get("rows", [])),
        "family_count": len(accessories.get("families", [])),
        "source_file": accessories.get("source_file"),
    }

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["url_for"] = _url_for_stub
    html = env.get_template("index.html").render(
        sections=sections,
        category_blocks=blocks,
        total_skus=total_skus,
        accessories_summary=acc_summary,
    )

    # The static build needs catalog-engine.js loaded BEFORE app.js so the
    # engine is in scope when app.js runs. Cheapest seam: inject the engine
    # script tag right before the existing app.js tag.
    # app.js is rendered via url_for so it already carries ?v=BUILD_VERSION;
    # catalog-engine.js is injected here so we need to add the cache-bust
    # query string explicitly.
    needle = f'<script src="static/app.js?v={BUILD_VERSION}">'
    inject = f'<script src="static/catalog-engine.js?v={BUILD_VERSION}"></script>\n  '
    if needle not in html:
        raise RuntimeError(
            "template missing expected app.js script tag — update inject anchor "
            "(remember Jinja url_for stub now appends ?v=BUILD_VERSION)."
        )
    html = html.replace(needle, inject + needle)

    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"[build]   wrote index.html — {(DOCS_DIR / 'index.html').stat().st_size / 1024:.1f} KB")

    print(f"\n[build] done. open {DOCS_DIR / 'index.html'} to preview, then commit docs/.")


if __name__ == "__main__":
    main()
