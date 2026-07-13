"use strict";

/* Static port of app/catalog.py's resolve + options engine.
   Catalog JSON is fetched on demand from ./data/<key>.json and cached.

   Each loaded catalog has the same fields as the Python ValveTypeConfig
   plus `colIndex` (Map<col, arrayIdx>) and `_keyToCol` (Map<cascadeKey, col>)
   for O(1) lookups against the compact `rows: [[...], ...]` payload.

   The 5 entry points mirror server.py:
     CatalogEngine.options(type, picks)
     CatalogEngine.resolve(type, picks)        -- also fills paired_actuators
     CatalogEngine.accessories()
     CatalogEngine.metadata()                  -- list of all known types
*/

/* Cache-bust data fetches with the SAME build version this script was loaded
   with (index.html loads it as `catalog-engine.js?v=BUILD_VERSION`). A new
   deploy => new version => browsers refetch the JSON instead of serving a stale
   cached copy; within one build the JSON still caches normally. Without this,
   data changes (e.g. a new accessory family) don't reach returning users until
   their cache expires. */
const DATA_VERSION = (() => {
  try {
    const src = document.currentScript && document.currentScript.src;
    const v = src && new URL(src).searchParams.get("v");
    return v ? `?v=${v}` : "";
  } catch (_) { return ""; }
})();

const CATALOG_KEYS = [
  "ball", "butterfly", "pneumatic_rp", "pneumatic_sy", "electrical_rotary",
];

const PAIRED_DASH_PREFIXES = ["SYA"];
const EA_QM_SLASH_RE = /^(EA|QM)-(\d+)([A-Z])$/;
// Control valve "Fail Safe" cells: "MSD-200 E" / "MSD-250D" -> family "MSD-200".
const MSD_FAMILY_RE = /^(MSD-\d+)\s*[A-Za-z]?$/;

function normalizePairedModel(model) {
  // Pattern 1: insert missing dash after letter prefix (SYA065 -> SYA-065).
  for (const p of PAIRED_DASH_PREFIXES) {
    if (model.startsWith(p) && !model.startsWith(p + "-")) {
      model = p + "-" + model.slice(p.length);
      break;
    }
  }
  // Pattern 2: insert missing slash before trailing letter (EA-21D -> EA-21/D).
  const m = EA_QM_SLASH_RE.exec(model);
  if (m) return `${m[1]}-${m[2]}/${m[3]}`;
  // Pattern 3: MSD model + variant letter -> family (MSD-200 E -> MSD-200).
  const msd = MSD_FAMILY_RE.exec(model);
  if (msd) return msd[1];
  return model;
}

function resolvePairedTargetType(paired, model) {
  if (paired.target_by_prefix && paired.target_by_prefix.length) {
    for (const [prefix, tt] of paired.target_by_prefix) {
      if (model.startsWith(prefix)) return tt;
    }
    return null;
  }
  return paired.target_type;
}

class CatalogEngine {
  constructor() {
    this._cache = new Map();    // key -> Promise<loadedCatalog>
    this._byKey = new Map();    // key -> loadedCatalog (resolved)
  }

  /* Returns a promise resolving the loaded+indexed catalog. */
  async load(key) {
    if (this._cache.has(key)) return this._cache.get(key);
    const p = fetch(`./data/${key}.json${DATA_VERSION}`).then(async (resp) => {
      if (!resp.ok) throw new Error(`load ${key}: HTTP ${resp.status}`);
      const cat = await resp.json();
      cat.colIndex = new Map(cat.columns_used.map((c, i) => [c, i]));
      cat.keyToCol = new Map(cat.cascade.map((f) => [f.key, f.col]));
      this._byKey.set(key, cat);
      return cat;
    });
    this._cache.set(key, p);
    return p;
  }

  _cell(cat, row, col) {
    const i = cat.colIndex.get(col);
    return i === undefined ? null : row[i];
  }

  _filter(cat, picks) {
    if (!picks || Object.keys(picks).length === 0) return cat.rows;
    const constraints = [];
    for (const [k, v] of Object.entries(picks)) {
      const col = cat.keyToCol.get(k);
      if (col === undefined) continue;
      constraints.push([cat.colIndex.get(col), String(v)]);
    }
    return cat.rows.filter((row) => {
      for (const [idx, want] of constraints) {
        if (String(row[idx]) !== want) return false;
      }
      return true;
    });
  }

  async options(key, picks) {
    const cat = await this.load(key);
    const matched = this._filter(cat, picks);
    const out = {};
    for (const f of cat.cascade) {
      if (picks && f.key in picks) continue;
      const idx = cat.colIndex.get(f.col);
      const vals = new Set();
      for (const row of matched) {
        const v = row[idx];
        if (v !== null && v !== undefined) vals.add(v);
      }
      out[f.key] = Array.from(vals).sort((a, b) => {
        const sa = String(a), sb = String(b);
        if (sa.length !== sb.length) return sa.length - sb.length;
        return sa < sb ? -1 : sa > sb ? 1 : 0;
      });
    }
    return out;
  }

  async resolve(key, picks) {
    const cat = await this.load(key);
    const matched = this._filter(cat, picks);
    if (matched.length === 0) return { matched: false };
    const row = matched[0];
    const detail = {
      match_count: matched.length,
      fields: cat.detail_columns.map((dc) => ({
        label: dc.label,
        value: this._cell(cat, row, dc.col),
      })),
      primary: this._cell(cat, row, cat.primary_col),
      secondary: cat.secondary_col ? this._cell(cat, row, cat.secondary_col) : null,
    };
    if (cat.show_bto_fos) {
      const bto = this._cell(cat, row, cat.bto_col);
      detail.bto = bto;
      const n = bto === null || bto === "" ? null : Number(bto);
      detail.fos = Number.isFinite(n) ? n * 1.5 : null;
    }

    // Paired actuators — faithful port of catalog.py Catalog.resolve()
    // (+ server.py name enrichment). MUST match the Flask backend exactly:
    //   * skip blank / "#N/A" cells (no recommendation at that position);
    //   * dedup by (target_type, model) ONLY — a model recommended at several
    //     pressures collapses to ONE chip (the first label wins);
    //   * keep every other value (incl. literal "0" / Excel error strings) as a
    //     real chip — the name lookup below marks unmatched ones
    //     `not_in_catalog`, which app.js renders as a greyed 'data pending' slot.
    // Earlier this engine put the label in the dedup key and emitted blank-code
    // "empty" placeholders, which over-listed chips and showed code-less slots
    // on GitHub Pages while the Flask app stayed correct (2026-06-03 fix).
    // Dedup rule (mirrors catalog.py Catalog.resolve, user's choice 2026-06-04):
    //   * DOUBLE-ACTING pressure slots (label has BOTH "Double Acting" and "@")
    //     show every pressure even when the same code repeats (ACT-050D at
    //     3.5/4/5.5 bar -> 3 chips).
    //   * EVERYTHING ELSE (Spring-Return at any pressure, Electric, Linear,
    //     generic alternatives) dedupes by code: one chip per distinct code.
    const seenModels = new Set();   // `${tt}|${model}`
    const seenSlots = new Set();    // `${tt}|${model}|${label}`
    // Per-series actuator labels (mirror of catalog.py Catalog.resolve): look up
    // the row's controlling-field value (e.g. Series) so 5016 shows "A Port
    // Close"/"B Port Close" while other series keep the generic labels.
    const ovKey = cat.cascade_override_key ||
                  (cat.cascade[0] && cat.cascade[0].key) || null;
    const ovCol = ovKey ? cat.keyToCol.get(ovKey) : null;
    const rowSeries = ovCol != null ? this._cell(cat, row, ovCol) : null;
    const labelFor = (pa) => {
      if (rowSeries && pa.series_labels) {
        const sv = String(rowSeries).trim();
        for (const prefix of Object.keys(pa.series_labels)) {
          if (sv.startsWith(prefix)) return pa.series_labels[prefix];
        }
      }
      return pa.label;
    };
    const paired = [];
    for (const pa of cat.paired_actuators || []) {
      const raw = this._cell(cat, row, pa.model_col);
      if (raw === null || raw === undefined || raw === "") continue;
      const model = normalizePairedModel(String(raw).trim());
      if (model === "" || model === "#N/A") continue;
      // Dual-use column guard (mirrors catalog.py): skip non-model values
      // (e.g. control valve Fail-Safe cells holding a pressure or 0).
      if (pa.require_prefix && !model.startsWith(pa.require_prefix)) continue;
      const target_type = resolvePairedTargetType(pa, model);
      if (pa.label.includes("Double Acting") && pa.label.includes("@")) {  // DA pressure slot
        const slot = `${target_type}|${model}|${pa.label}`;
        if (seenSlots.has(slot)) continue;
        seenSlots.add(slot);
      } else if (seenModels.has(`${target_type}|${model}`)) {  // everything else — one per code
        continue;
      }
      seenModels.add(`${target_type}|${model}`);
      paired.push({
        model,
        target_type,
        target_field: pa.target_field,
        label: labelFor(pa),
      });
    }
    if (paired.length) {
      for (const p of paired) {
        const targetCat = p.target_type ? await this._safeLoad(p.target_type) : null;
        if (!targetCat) {
          p.name = null;
          p.not_in_catalog = true;
          continue;
        }
        const { found, name } = this._lookupPaired(targetCat, p.target_field, p.model);
        p.name = name;
        p.not_in_catalog = !found;
      }
      detail.paired_actuators = paired;
    }

    return { matched: true, detail };
  }

  async _safeLoad(key) {
    try { return await this.load(key); }
    catch { return null; }
  }

  _lookupPaired(targetCat, fieldKey, modelValue) {
    const col = targetCat.keyToCol.get(fieldKey);
    if (col === undefined) return { found: false, name: null };
    const idx = targetCat.colIndex.get(col);
    const want = String(modelValue);
    for (const row of targetCat.rows) {
      if (String(row[idx]) !== want) continue;
      // Build friendly name from "Actuator" + "Type" detail columns.
      const wanted = new Set(["Actuator", "Type"]);
      const parts = [];
      for (const dc of targetCat.detail_columns) {
        if (!wanted.has(dc.label)) continue;
        const v = this._cell(targetCat, row, dc.col);
        if (v !== null && v !== undefined && String(v).trim() !== "") {
          parts.push(String(v).trim());
        }
      }
      return { found: true, name: parts.length ? parts.join(" — ") : null };
    }
    return { found: false, name: null };
  }

  async accessories() {
    if (this._accessories) return this._accessories;
    this._accessories = fetch(`./data/accessories.json${DATA_VERSION}`).then((r) => r.json());
    return this._accessories;
  }
}

window.CatalogEngine = new CatalogEngine();
